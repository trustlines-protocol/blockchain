import logging
import logging.config
import os
import signal
import sys

import click
import gevent
import gevent.pool
from eth_keys.datatypes import PrivateKey
from eth_utils import to_checksum_address
from gevent.queue import Queue
from marshmallow.exceptions import ValidationError
from toml.decoder import TomlDecodeError
from web3 import HTTPProvider, Web3

import bridge.node_status
import bridge.version
from bridge.config import load_config
from bridge.confirmation_sender import (
    ConfirmationSender,
    ConfirmationWatcher,
    make_sanity_check_transfer,
)
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
from bridge.transfer_recorder import TransferRecorder
from bridge.utils import get_validator_private_key
from bridge.validator_balance_watcher import ValidatorBalanceWatcher
from bridge.validator_status_watcher import ValidatorStatusWatcher
from bridge.webservice import InternalState, Webservice

logger = logging.getLogger(__name__)


class SetupError(Exception):
    pass


def configure_logging(config):
    """configure the logging subsystem via the 'logging' key in the TOML config"""
    try:
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


def make_w3(config, chain: ChainRole):
    chaincfg = config[chain.configuration_key]
    return Web3(
        HTTPProvider(
            chaincfg["rpc_url"], request_kwargs={"timeout": chaincfg["rpc_timeout"]}
        )
    )


def make_w3_home(config):
    return make_w3(config, ChainRole.home)


def make_w3_foreign(config):
    return make_w3(config, ChainRole.foreign)


def get_max_pending_transactions(config):
    return min(
        (config["home_chain"]["max_reorg_depth"] + 1)
        * config["home_chain"]["max_pending_transactions_per_block"],
        512,
    )


def make_validator_address(config):
    private_key_bytes = get_validator_private_key(config)
    return PrivateKey(private_key_bytes).public_key.to_canonical_address()


def sanity_check_home_bridge_contracts(home_bridge_contract):
    validate_contract_existence(home_bridge_contract)

    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)

    try:
        validate_contract_existence(validator_proxy_contract)
    except ValueError as error:
        raise SetupError(
            "Serious bridge setup error. The validator proxy contract at the address the home "
            "bridge property points to does not exist or is not intact!"
        ) from error

    balance = home_bridge_contract.web3.eth.getBalance(home_bridge_contract.address)
    if balance == 0:
        raise SetupError("Serious bridge setup error. The bridge has no funds.")


def make_transfer_event_fetcher(config, transfer_event_queue):
    w3_foreign = make_w3_foreign(config)
    token_contract = w3_foreign.eth.contract(
        address=config["foreign_chain"]["token_contract_address"],
        abi=MINIMAL_ERC20_TOKEN_ABI,
    )
    return EventFetcher(
        web3=w3_foreign,
        contract=token_contract,
        filter_definition={
            TRANSFER_EVENT_NAME: {
                "to": config["foreign_chain"]["bridge_contract_address"]
            }
        },
        event_queue=transfer_event_queue,
        max_reorg_depth=config["foreign_chain"]["max_reorg_depth"],
        start_block_number=config["foreign_chain"]["event_fetch_start_block_number"],
        chain_role=ChainRole.foreign,
    )


def make_home_bridge_event_fetcher(config, home_bridge_event_queue):
    w3_home = make_w3_home(config)
    home_bridge_contract = w3_home.eth.contract(
        address=config["home_chain"]["bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    validator_address = make_validator_address(config)

    return EventFetcher(
        web3=w3_home,
        contract=home_bridge_contract,
        filter_definition={
            CONFIRMATION_EVENT_NAME: {"validator": validator_address},
            COMPLETION_EVENT_NAME: {},
        },
        event_queue=home_bridge_event_queue,
        max_reorg_depth=config["home_chain"]["max_reorg_depth"],
        start_block_number=config["home_chain"]["event_fetch_start_block_number"],
        chain_role=ChainRole.home,
    )


def make_recorder(config):
    minimum_balance = config["home_chain"]["minimum_validator_balance"]
    return TransferRecorder(minimum_balance)


def make_confirmation_task_planner(
    config,
    recorder,
    control_queue,
    transfer_event_queue,
    home_bridge_event_queue,
    confirmation_task_queue,
):
    return ConfirmationTaskPlanner(
        sync_persistence_time=HOME_CHAIN_STEP_DURATION,
        recorder=recorder,
        control_queue=control_queue,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )


def make_confirmation_sender(
    *, config, pending_transaction_queue, confirmation_task_queue
):
    w3_home = make_w3_home(config)

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_chain"]["bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)
    return ConfirmationSender(
        transfer_event_queue=confirmation_task_queue,
        home_bridge_contract=home_bridge_contract,
        private_key=get_validator_private_key(config),
        gas_price=config["home_chain"]["gas_price"],
        max_reorg_depth=config["home_chain"]["max_reorg_depth"],
        pending_transaction_queue=pending_transaction_queue,
        sanity_check_transfer=make_sanity_check_transfer(
            foreign_bridge_contract_address=to_checksum_address(
                config["foreign_chain"]["bridge_contract_address"]
            )
        ),
    )


def make_confirmation_watcher(*, config, pending_transaction_queue):
    w3_home = make_w3_home(config)
    max_reorg_depth = config["home_chain"]["max_reorg_depth"]
    return ConfirmationWatcher(
        w3=w3_home,
        pending_transaction_queue=pending_transaction_queue,
        max_reorg_depth=max_reorg_depth,
    )


def make_validator_status_watcher(config, control_queue):
    w3_home = make_w3_home(config)

    home_bridge_contract = w3_home.eth.contract(
        address=config["home_chain"]["bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)
    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)

    validator_address = make_validator_address(config)

    return ValidatorStatusWatcher(
        validator_proxy_contract,
        validator_address,
        poll_interval=HOME_CHAIN_STEP_DURATION,
        control_queue=control_queue,
        stop_validating_callback=shutdown,
    )


def make_validator_balance_watcher(config, control_queue):
    w3 = make_w3_home(config)

    validator_address = make_validator_address(config)

    poll_interval = config["home_chain"]["balance_warn_poll_interval"]

    return ValidatorBalanceWatcher(
        w3=w3,
        validator_address=validator_address,
        poll_interval=poll_interval,
        control_queue=control_queue,
    )


public_config_keys = ()


def make_webservice(*, config, recorder):
    d = config["webservice"]
    if d and d["enabled"]:
        ws = Webservice(host=d["host"], port=d["port"])
    else:
        return None

    def encode_address(v):
        if isinstance(v, bytes):
            return to_checksum_address(v)
        else:
            return v

    public_config = {k: encode_address(config[k]) for k in public_config_keys}

    ws.enable_internal_state(InternalState(recorder=recorder, config=public_config))
    return ws


def make_main_services(config, recorder):
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
        recorder=recorder,
        control_queue=control_queue,
        transfer_event_queue=transfer_event_queue,
        home_bridge_event_queue=home_bridge_event_queue,
        confirmation_task_queue=confirmation_task_queue,
    )

    validator_status_watcher = make_validator_status_watcher(config, control_queue)

    max_pending_transactions = get_max_pending_transactions(config)
    logger.info("maximum number of pending transactions: %s", max_pending_transactions)
    pending_transaction_queue = Queue(max_pending_transactions)
    sender = make_confirmation_sender(
        config=config,
        pending_transaction_queue=pending_transaction_queue,
        confirmation_task_queue=confirmation_task_queue,
    )
    watcher = make_confirmation_watcher(
        config=config, pending_transaction_queue=pending_transaction_queue
    )

    validator_balance_watcher = make_validator_balance_watcher(config, control_queue)

    return (
        [
            Service(
                "fetch-foreign-bridge-events",
                transfer_event_fetcher.fetch_events,
                config["foreign_chain"]["event_poll_interval"],
            ),
            Service(
                "fetch-home-bridge-events",
                home_bridge_event_fetcher.fetch_events,
                config["home_chain"]["event_poll_interval"],
            ),
            Service("validator-status-watcher", validator_status_watcher.run),
            Service("validator_balance_watcher", validator_balance_watcher.run),
            Service("log-internal-state", log_internal_state, recorder),
        ]
        + sender.services
        + watcher.services
        + confirmation_task_planner.services
    )


def reload_logging_config(config_path):
    logger.info(f"Trying to reload the logging configuration from {config_path}")
    try:
        config = load_config(config_path)
        configure_logging(config)
        logger.info("Logging has been reconfigured")
    except Exception as err:
        # this function is being called as signal handler. make sure
        # we don't die as this would raise the error in the main
        # greenlet.
        logger.critical(
            f"Error while trying to reload the logging configuration from {config_path}: {err}"
        )


def install_signal_handler(signum, name, f, *args, **kwargs):
    def handler():
        gevent.getcurrent().name = name
        logger.info(f"Received {signal.Signals(signum).name} signal.")
        f(*args, **kwargs)

    gevent.signal(signum, handler)


def log_internal_state(recorder):
    while True:
        gevent.sleep(60.0)
        recorder.log_current_state()


main_pool = gevent.pool.Pool()


def shutdown_raw(timeout=APPLICATION_CLEANUP_TIMEOUT, exitcode=0):
    """gracefully shut down the application"""
    logger.info("Stopping with exitcode %s", exitcode)

    timeout = gevent.Timeout(timeout)
    timeout.start()
    try:
        main_pool.kill()
        main_pool.join()
    except gevent.Timeout as handled_timeout:
        if handled_timeout is not timeout:
            logger.error("Catched wrong timeout exception, exciting anyway")
        else:
            logger.error("Bridge didn't clean up in time, doing a hard exit")

        sys.stderr.flush()
        sys.stdout.flush()

        os._exit(os.EX_SOFTWARE)
    os._exit(exitcode)


def shutdown(timeout=APPLICATION_CLEANUP_TIMEOUT, exitcode=0):
    """call shutdown_raw in a new greenlet. we need to call that one,
    if the calling greenlet is running inside the main_pool"""
    gevent.spawn(shutdown_raw, timeout=timeout, exitcode=exitcode)


def handle_greenlet_exception(gr):
    logger.exception(
        f"Application Error: {gr.name} unexpectedly died. Shutting down.",
        exc_info=gr.exception,
    )
    shutdown_raw(exitcode=os.EX_SOFTWARE)


def start_services_in_main_pool(services):
    return start_services(
        services,
        start=main_pool.start,
        link_exception_callback=handle_greenlet_exception,
    )


def wait_for_node_fully_synced(config, chain):
    w3 = make_w3(config, chain)
    start_block = config[chain.configuration_key]["event_fetch_start_block_number"]

    def is_synced(node_status):
        syncmsg = "still syncing" if node_status.is_syncing else "fully synced"
        start_block_reached = node_status.latest_synced_block >= start_block
        start_block_msg = "reached" if start_block_reached else "not reached"
        logger.info(
            f"{chain.name} node {syncmsg}, start block {start_block} {start_block_msg}: {node_status}"
        )
        return not node_status.is_syncing and start_block_reached

    bridge.node_status.wait_for_node_status(w3, is_synced)
    logger.info(f"{chain.name} node is fully synced")


def wait_until_home_node_is_ready(config):
    wait_for_node_fully_synced(config, ChainRole.home)

    w3_home = make_w3_home(config)
    home_bridge_contract = w3_home.eth.contract(
        address=config["home_chain"]["bridge_contract_address"], abi=HOME_BRIDGE_ABI
    )
    sanity_check_home_bridge_contracts(home_bridge_contract)
    logger.info("home node has passed the sanity checks")


def wait_until_foreign_node_is_ready(config):
    wait_for_node_fully_synced(config, ChainRole.foreign)

    w3_foreign = make_w3_foreign(config)
    token_contract = w3_foreign.eth.contract(
        address=config["foreign_chain"]["token_contract_address"],
        abi=MINIMAL_ERC20_TOKEN_ABI,
    )
    validate_contract_existence(token_contract)
    logger.info("foreign node has passed the sanity checks")


def start_system(config):
    recorder = make_recorder(config)
    install_signal_handler(
        signal.SIGUSR1, "report-internal-state", recorder.log_current_state
    )

    webservice = make_webservice(config=config, recorder=recorder)
    if webservice is not None:
        start_services_in_main_pool(webservice.services)

    wait_node_ready_services = [
        Service("home_wait_ready", wait_until_home_node_is_ready, config),
        Service("foreign_wait_ready", wait_until_foreign_node_is_ready, config),
    ]

    gevent.joinall(
        start_services_in_main_pool(wait_node_ready_services), raise_error=True
    )

    main_services = make_main_services(config, recorder)
    start_services_in_main_pool(main_services)


@click.command()
@click.version_option(version=bridge.version.version)
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True),
    required=True,
    envvar="BRIDGE_CONFIG",
    help="Path to a config file",
)
@click.pass_context
def main(ctx, config_path: str) -> None:
    """The Trustlines Bridge Validation Server

    Configuration can be made using a TOML file.

    See config.py for valid configuration options and defaults.
    """

    try:
        logger.info(f"Loading configuration file from {config_path}")
        config = load_config(config_path)
    except TomlDecodeError as decode_error:
        raise click.UsageError(f"Invalid config file: {decode_error}") from decode_error
    except ValidationError as validation_error:
        raise click.UsageError(
            f"Invalid config file: {validation_error}"
        ) from validation_error

    configure_logging(config)

    validator_address = make_validator_address(config)
    logger.info(
        f"Starting Trustlines Bridge Validation Server for address {to_checksum_address(validator_address)}"
    )
    install_signal_handler(
        signal.SIGHUP, "reload-logging-config", reload_logging_config, config_path
    )

    for signum in [signal.SIGINT, signal.SIGTERM]:
        install_signal_handler(signum, "terminator", shutdown_raw, exitcode=0)

    try:
        start_services_in_main_pool([Service("start_system", start_system, config)])
    except Exception as exception:
        logger.exception("Application error", exc_info=exception)
        os._exit(os.EX_SOFTWARE)
    finally:
        gevent.hub.get_hub().join()
