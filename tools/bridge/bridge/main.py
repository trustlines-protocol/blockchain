from gevent import monkey  # isort:skip

monkey.patch_all()  # noqa: E402 isort:skip

import logging
import logging.config
import os

import click
import gevent
import gevent.pool
from eth_keys.datatypes import PrivateKey
from gevent.queue import Queue
from toml.decoder import TomlDecodeError
from web3 import HTTPProvider, Web3

from bridge.config import load_config
from bridge.confirmation_sender import ConfirmationSender
from bridge.confirmation_task_planner import ConfirmationTaskPlanner
from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    HOME_CHAIN_STEP_DURATION,
    TRANSFER_EVENT_NAME,
)
from bridge.contract_abis import HOME_BRIDGE_ABI, MINIMAL_ERC20_TOKEN_ABI
from bridge.contract_validation import (
    get_validator_proxy_contract,
    validate_contract_existence,
)
from bridge.event_fetcher import EventFetcher

logger = logging.getLogger(__name__)


def configure_logging(config):
    """configure the logging subsystem via the 'logging' key in the TOML config"""
    try:
        logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())
        logging.config.dictConfig(config["logging"])
    except (ValueError, TypeError, AttributeError, ImportError) as err:
        click.echo(
            f"Error configuring logging: {err}\n"
            "Please check your configuration file and the LOGLEVEL environment variable"
        )
        raise click.Abort()

    logger.debug(
        "Initialized logging system with the following config: %r", config["logging"]
    )


def make_w3_home(config):
    return Web3(
        HTTPProvider(
            config["home_rpc_url"],
            request_kwargs={"timeout": config["home_rpc_timeout"]},
        )
    )


def make_w3_foreign(config):
    return Web3(
        HTTPProvider(
            config["foreign_rpc_url"],
            request_kwargs={"timeout": config["foreign_rpc_timeout"]},
        )
    )


def sanity_check_home_bridge_contract(home_bridge_contract):
    validate_contract_existence(home_bridge_contract)

    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)

    try:
        validate_contract_existence(validator_proxy_contract)
    except ValueError as error:
        raise ValueError(
            f"Serious bridge setup error. The validator proxy contract at the address the home "
            f"bridge property points to does not exist or is not intact!"
        ) from error


def make_transfer_event_fetcher(config, transfer_event_queue):
    w3_foreign = make_w3_foreign(config)
    token_contract = w3_foreign.eth.contract(
        address=config["foreign_chain_token_contract_address"],
        abi=MINIMAL_ERC20_TOKEN_ABI,
    )
    validate_contract_existence(token_contract)
    return EventFetcher(
        web3=w3_foreign,
        contract=token_contract,
        filter_definition={
            TRANSFER_EVENT_NAME: {"to": config["foreign_bridge_contract_address"]}
        },
        event_queue=transfer_event_queue,
        max_reorg_depth=config["foreign_chain_max_reorg_depth"],
        start_block_number=config["foreign_chain_event_fetch_start_block_number"],
    )


def make_home_bridge_event_fetcher(config, home_bridge_event_queue):
    w3_home = make_w3_home(config)
    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contract(home_bridge_contract)

    validator_address = PrivateKey(
        config["validator_private_key"]
    ).public_key.to_canonical_address()

    return EventFetcher(
        web3=w3_home,
        contract=home_bridge_contract,
        filter_definition={
            CONFIRMATION_EVENT_NAME: {"validator": validator_address},
            COMPLETION_EVENT_NAME: {},
        },
        event_queue=home_bridge_event_queue,
        max_reorg_depth=config["home_chain_max_reorg_depth"],
        start_block_number=config["home_chain_event_fetch_start_block_number"],
    )


def make_confirmation_sender(config, confirmation_task_queue):
    w3_home = make_w3_home(config)

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contract(home_bridge_contract)

    return ConfirmationSender(
        transfer_event_queue=confirmation_task_queue,
        home_bridge_contract=home_bridge_contract,
        private_key=config["validator_private_key"],
        gas_price=config["home_chain_gas_price"],
        max_reorg_depth=config["home_chain_max_reorg_depth"],
    )


@click.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True),
    required=False,
    help="Path to a config file",
)
def main(config_path: str) -> None:
    """The Trustlines Bridge Validation Server

    Configuration can be made using a TOML file or via Environment Variables.
    A dotenv (.env) file will be automatically evaluated.

    See .env.example and config.py for valid configuration options and defaults.
    """

    try:
        config = load_config(config_path)
    except TomlDecodeError as decode_error:
        raise click.UsageError(f"Invalid config file: {decode_error}") from decode_error
    except ValueError as value_error:
        raise click.UsageError(f"Invalid config file: {value_error}") from value_error

    configure_logging(config)
    validator_address = PrivateKey(
        config["validator_private_key"]
    ).public_key.to_checksum_address()

    logger.info(
        f"Starting Trustlines Bridge Validation Server for address {validator_address}"
    )

    transfer_event_queue = Queue()
    home_bridge_event_queue = Queue()
    confirmation_task_queue = Queue()

    transfer_event_fetcher = make_transfer_event_fetcher(config, transfer_event_queue)
    home_bridge_event_fetcher = make_home_bridge_event_fetcher(
        config, home_bridge_event_queue
    )

    confirmation_task_planner = ConfirmationTaskPlanner(
        sync_persistence_time=HOME_CHAIN_STEP_DURATION,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )

    confirmation_sender = make_confirmation_sender(config, confirmation_task_queue)

    coroutines_and_args = [
        (
            transfer_event_fetcher.fetch_events,
            config["foreign_chain_event_poll_interval"],
        ),
        (
            home_bridge_event_fetcher.fetch_events,
            config["home_chain_event_poll_interval"],
        ),
        (confirmation_task_planner.run,),
        (confirmation_sender.run,),
    ]

    pool = gevent.pool.Pool()
    try:
        for coroutine_and_args in coroutines_and_args:
            pool.spawn(*coroutine_and_args)
        pool.join(raise_error=True)
    finally:
        pool.kill()
        pool.join()
