from gevent import monkey  # isort:skip

monkey.patch_all()  # noqa: E402 isort:skip

import logging
import os

import click
import gevent
from eth_keys.datatypes import PrivateKey
from gevent import Greenlet
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

    logging.basicConfig(level=os.environ.get("LOGLEVEL", "INFO").upper())

    logging.info("Starting Trustlines Bridge Validation Server")

    try:
        config = load_config(config_path)
    except TomlDecodeError as decode_error:
        raise click.UsageError(f"Invalid config file: {decode_error}") from decode_error
    except ValueError as value_error:
        raise click.UsageError(f"Invalid config file: {value_error}") from value_error

    w3_foreign = Web3(
        HTTPProvider(
            config["foreign_rpc_url"],
            request_kwargs={"timeout": config["foreign_rpc_timeout"]},
        )
    )
    w3_home = Web3(
        HTTPProvider(
            config["home_rpc_url"],
            request_kwargs={"timeout": config["home_rpc_timeout"]},
        )
    )

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    validate_contract_existence(home_bridge_contract)

    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)

    try:
        validate_contract_existence(validator_proxy_contract)

    except ValueError as error:
        raise ValueError(
            f"Serious bridge setup error. The validator proxy contract at the address the home "
            f"bridge property points to does not exist or is not intact!"
        ) from error

    token_contract = w3_foreign.eth.contract(
        address=config["foreign_chain_token_contract_address"],
        abi=MINIMAL_ERC20_TOKEN_ABI,
    )
    validate_contract_existence(token_contract)

    validator_private_key = config["validator_private_key"]
    validator_address = PrivateKey(
        validator_private_key
    ).public_key.to_canonical_address()

    transfer_event_queue = Queue()
    home_bridge_event_queue = Queue()
    confirmation_task_queue = Queue()

    transfer_event_fetcher = EventFetcher(
        web3=w3_foreign,
        contract=token_contract,
        filter_definition={
            TRANSFER_EVENT_NAME: {"to": config["foreign_bridge_contract_address"]}
        },
        event_queue=transfer_event_queue,
        max_reorg_depth=config["foreign_chain_max_reorg_depth"],
        start_block_number=config["foreign_chain_event_fetch_start_block_number"],
    )
    home_bridge_event_fetcher = EventFetcher(
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
    confirmation_task_planner = ConfirmationTaskPlanner(
        sync_persistence_time=HOME_CHAIN_STEP_DURATION,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )
    confirmation_sender = ConfirmationSender(
        transfer_event_queue=confirmation_task_queue,
        home_bridge_contract=home_bridge_contract,
        private_key=config["validator_private_key"],
        gas_price=config["home_chain_gas_price"],
        max_reorg_depth=config["home_chain_max_reorg_depth"],
    )

    try:
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
        greenlets = [
            Greenlet.spawn(*coroutine_and_args)
            for coroutine_and_args in coroutines_and_args
        ]
        gevent.joinall(greenlets, raise_error=True)
    finally:
        for greenlet in greenlets:
            greenlet.kill()
