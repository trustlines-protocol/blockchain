from gevent import monkey  # isort:skip

monkey.patch_all()  # noqa: E402 isort:skip

import logging
import logging.config
import os
import signal
from functools import partial

import click
import gevent
import gevent.pool
from eth_keys.datatypes import PrivateKey
from eth_utils import to_checksum_address
from gevent.queue import Queue
from toml.decoder import TomlDecodeError
from web3 import HTTPProvider, Web3

from bridge.config import load_config
from bridge.confirmation_sender import ConfirmationSender, make_sanity_check_transfer
from bridge.confirmation_task_planner import ConfirmationTaskPlanner
from bridge.constants import (
    APPLICATION_CLEANUP_TIMEOUT,
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
from bridge.events import ChainRole
from bridge.service import Service, start_services
from bridge.validator_balance_watcher import ValidatorBalanceWatcher
from bridge.validator_status_watcher import ValidatorStatusWatcher

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


def make_validator_address(config):
    return PrivateKey(config["validator_private_key"]).public_key.to_canonical_address()


def sanity_check_home_bridge_contracts(home_bridge_contract):
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
        chain_role=ChainRole.foreign,
    )


def make_home_bridge_event_fetcher(config, home_bridge_event_queue):
    w3_home = make_w3_home(config)
    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)

    validator_address = make_validator_address(config)

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
        chain_role=ChainRole.home,
    )


def make_confirmation_task_planner(
    config,
    control_queue,
    transfer_event_queue,
    home_bridge_event_queue,
    confirmation_task_queue,
):
    minimum_balance = config["minimum_validator_balance"]

    return ConfirmationTaskPlanner(
        sync_persistence_time=HOME_CHAIN_STEP_DURATION,
        minimum_balance=minimum_balance,
        control_queue=control_queue,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )


def make_confirmation_sender(config, confirmation_task_queue):
    w3_home = make_w3_home(config)

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)

    return ConfirmationSender(
        transfer_event_queue=confirmation_task_queue,
        home_bridge_contract=home_bridge_contract,
        private_key=config["validator_private_key"],
        gas_price=config["home_chain_gas_price"],
        max_reorg_depth=config["home_chain_max_reorg_depth"],
        sanity_check_transfer=make_sanity_check_transfer(
            foreign_bridge_contract_address=to_checksum_address(
                config["foreign_bridge_contract_address"]
            )
        ),
    )


def make_validator_status_watcher(config, control_queue, stop):
    w3_home = make_w3_home(config)

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)
    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)

    validator_address = make_validator_address(config)

    return ValidatorStatusWatcher(
        validator_proxy_contract,
        validator_address,
        poll_interval=HOME_CHAIN_STEP_DURATION,
        control_queue=control_queue,
        stop_validating_callback=stop,
    )


def make_validator_balance_watcher(config, control_queue):
    w3 = make_w3_home(config)

    validator_address = make_validator_address(config)

    poll_interval = config["balance_warn_poll_interval"]

    return ValidatorBalanceWatcher(
        w3=w3,
        validator_address=validator_address,
        poll_interval=poll_interval,
        control_queue=control_queue,
    )


def stop(pool, timeout):
    logger.info("Stopping...")

    timeout = gevent.Timeout(timeout)
    timeout.start()
    try:
        pool.kill()
        pool.join()
    except gevent.Timeout as handled_timeout:
        if handled_timeout is not timeout:
            logger.error("Catched wrong timeout exception, exciting anyway")
        else:
            logger.error("Bridge didn't clean up in time, doing a hard exit")
        os._exit(os.EX_SOFTWARE)


@click.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True),
    required=False,
    envvar="BRIDGE_CONFIG",
    help="Path to a config file",
)
@click.pass_context
def main(ctx, config_path: str) -> None:
    """The Trustlines Bridge Validation Server

    Configuration can be made using a TOML file or via environment variables. Tools such as dotenv
    or envdir may simplify setting environment variables. For a dotenv example, see `.env.example`.

    See config.py for valid configuration options and defaults.
    """

    try:
        config = load_config(config_path)
    except TomlDecodeError as decode_error:
        raise click.UsageError(f"Invalid config file: {decode_error}") from decode_error
    except ValueError as value_error:
        raise click.UsageError(f"Invalid config file: {value_error}") from value_error

    configure_logging(config)

    validator_address = make_validator_address(config)
    logger.info(
        f"Starting Trustlines Bridge Validation Server for address {to_checksum_address(validator_address)}"
    )

    pool = gevent.pool.Pool()
    stop_pool = partial(stop, pool, APPLICATION_CLEANUP_TIMEOUT)

    control_queue = Queue()
    transfer_event_queue = Queue()
    home_bridge_event_queue = Queue()
    confirmation_task_queue = Queue()

    transfer_event_fetcher = make_transfer_event_fetcher(config, transfer_event_queue)
    home_bridge_event_fetcher = make_home_bridge_event_fetcher(
        config, home_bridge_event_queue
    )

    confirmation_task_planner = make_confirmation_task_planner(
        config,
        control_queue=control_queue,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )

    validator_status_watcher = make_validator_status_watcher(
        config, control_queue, stop_pool
    )

    confirmation_sender = make_confirmation_sender(config, confirmation_task_queue)

    validator_balance_watcher = make_validator_balance_watcher(config, control_queue)

    services = (
        [
            Service(
                "fetch-foreign-bridge-events",
                transfer_event_fetcher.fetch_events,
                config["foreign_chain_event_poll_interval"],
            ),
            Service(
                "fetch-home-bridge-events",
                home_bridge_event_fetcher.fetch_events,
                config["home_chain_event_poll_interval"],
            ),
            Service("validator-status-watcher", validator_status_watcher.run),
            Service("validator_balance_watcher", validator_balance_watcher.run),
        ]
        + confirmation_task_planner.services
        + confirmation_sender.services
    )

    for signum in [signal.SIGINT, signal.SIGTERM]:
        gevent.signal(signum, stop_pool)

    try:
        greenlets = start_services(services, start=pool.start)
        gevent.joinall(greenlets, raise_error=True)
    except Exception as exception:
        logger.exception("Application error", exc_info=exception)
        stop(pool, APPLICATION_CLEANUP_TIMEOUT)
