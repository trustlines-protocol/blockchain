import logging
import logging.config
import os
import signal
import sys
from functools import partial

import click
import gevent
import gevent.pool
import tenacity
from eth_keys.datatypes import PrivateKey
from eth_utils import to_checksum_address
from gevent.queue import Queue
from marshmallow.exceptions import ValidationError
from toml.decoder import TomlDecodeError
from web3 import HTTPProvider, Web3

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


def wait_for_chain_synced_until_block(w3, start_block_number, timeout, chain_role):
    retry = tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=5, max=timeout),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
    )

    @retry
    def _rpc_syncing():
        return w3.eth.syncing

    @retry
    def _rpc_block_number():
        return w3.eth.blockNumber

    while True:
        syncing = _rpc_syncing()
        if syncing is False:
            highest_block_number = _rpc_block_number()
            current_block_number = highest_block_number
        else:
            current_block_number = syncing["currentBlock"]
            highest_block_number = syncing["highestBlock"]

        fully_synced = current_block_number == highest_block_number
        synced_to_start_block = current_block_number >= start_block_number

        if synced_to_start_block:
            if fully_synced:
                logger.info(
                    "%s node is fully synced to head number %d and has passed the event fetch start block number %d",
                    chain_role.value,
                    highest_block_number,
                    start_block_number,
                )
            else:
                logger.info(
                    "%s node is synced until block number %d of %d and has passed the event fetch "
                    "start block number %d",
                    chain_role.value,
                    current_block_number,
                    highest_block_number,
                    start_block_number,
                )
            break
        else:
            if fully_synced:
                logger.info(
                    "%s node is fully synced until head number %d, but chain hasn't reached event "
                    "fetch start block number %d yet. Waiting...",
                    chain_role.value,
                    highest_block_number,
                    start_block_number,
                )
            else:
                logger.info(
                    "%s node is synced until block number %d of %d, but hasn't reached event "
                    "fetch start block number %d yet. Waiting...",
                    chain_role.value,
                    current_block_number,
                    highest_block_number,
                    start_block_number,
                )
            gevent.sleep(HOME_CHAIN_STEP_DURATION)


def wait_for_chain_fully_synced_past_block(w3, start_block_number, timeout, chain_role):
    retry = tenacity.retry(
        wait=tenacity.wait_exponential(multiplier=1, min=5, max=timeout),
        before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
    )

    @retry
    def _rpc_syncing():
        return w3.eth.syncing

    @retry
    def _rpc_block_number():
        return w3.eth.blockNumber

    while True:
        syncing = _rpc_syncing()
        if syncing is False:
            highest_block_number = _rpc_block_number()
            current_block_number = highest_block_number
        else:
            current_block_number = syncing["currentBlock"]
            highest_block_number = syncing["highestBlock"]

        start_block_passed = current_block_number >= start_block_number

        if syncing:
            logger.info(
                "%s node is synced until block number %d of %d, but is not fully synced "
                "and not past start block number %d yet. Waiting...",
                chain_role.value,
                current_block_number,
                highest_block_number,
                start_block_number,
            )
        else:
            if start_block_passed:
                logger.info(
                    "%s node is fully synced to head number %d and has passed the event fetch start block number %d",
                    chain_role.value,
                    highest_block_number,
                    start_block_number,
                )
                break
            else:
                logger.info(
                    "%s node is fully synced until head number %d, but chain hasn't reached event "
                    "fetch start block number %d yet. Waiting...",
                    chain_role.value,
                    highest_block_number,
                    start_block_number,
                )
        gevent.sleep(HOME_CHAIN_STEP_DURATION)


def wait_for_start_blocks(config):
    w3_home = make_w3_home(config)
    w3_foreign = make_w3_foreign(config)

    home_chain_start_block_number = config["home_chain"][
        "event_fetch_start_block_number"
    ]
    foreign_chain_start_block_number = config["foreign_chain"][
        "event_fetch_start_block_number"
    ]

    home_chain_rpc_timeout = config["home_chain"]["rpc_timeout"]
    foreign_chain_rpc_timeout = config["home_chain"]["rpc_timeout"]

    wait_for_chain_synced_until_block(
        w3_home, home_chain_start_block_number, home_chain_rpc_timeout, ChainRole.home
    )
    wait_for_chain_fully_synced_past_block(
        w3_foreign,
        foreign_chain_start_block_number,
        foreign_chain_rpc_timeout,
        ChainRole.foreign,
    )


def make_w3_home(config):
    return Web3(
        HTTPProvider(
            config["home_chain"]["rpc_url"],
            request_kwargs={"timeout": config["home_chain"]["rpc_timeout"]},
        )
    )


def make_w3_foreign(config):
    return Web3(
        HTTPProvider(
            config["foreign_chain"]["rpc_url"],
            request_kwargs={"timeout": config["foreign_chain"]["rpc_timeout"]},
        )
    )


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
    validate_contract_existence(token_contract)
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


def make_validator_status_watcher(config, control_queue, stop):
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
        stop_validating_callback=stop,
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


def make_main_services(config, recorder, stop_pool):
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

    validator_status_watcher = make_validator_status_watcher(
        config, control_queue, stop_pool
    )

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

        sys.stderr.flush()
        sys.stdout.flush()

        os._exit(os.EX_SOFTWARE)


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

    pool = gevent.pool.Pool()
    stop_pool = partial(stop, pool, APPLICATION_CLEANUP_TIMEOUT)

    def handle_greenlet_exception(gr):
        logger.exception(
            f"Application Error: {gr.name} unexpectedly died. Shutting down.",
            exc_info=gr.exception,
        )
        stop_pool()

    recorder = make_recorder(config)

    webservice = make_webservice(config=config, recorder=recorder)
    wait_for_start_blocks_service = Service(
        "wait_for_start_block", wait_for_start_blocks, config
    )
    webservice_services = webservice.services if webservice is not None else []

    install_signal_handler(
        signal.SIGUSR1, "report-internal-state", recorder.log_current_state
    )

    install_signal_handler(
        signal.SIGHUP, "reload-logging-config", reload_logging_config, config_path
    )
    for signum in [signal.SIGINT, signal.SIGTERM]:
        install_signal_handler(signum, "terminator", stop_pool)

    try:
        webservice_greenlets = start_services(
            webservice_services,
            start=pool.start,
            link_exception_callback=handle_greenlet_exception,
        )
        start_block_greenlet, = start_services(
            [wait_for_start_blocks_service],
            start=pool.start,
            link_exception_callback=handle_greenlet_exception,
        )

        gevent.joinall([start_block_greenlet])

        # Only continue if start_block_greenlet wasn't killed
        if start_block_greenlet.successful() and not isinstance(
            start_block_greenlet.value, gevent.GreenletExit
        ):
            main_services = make_main_services(config, recorder, stop_pool)
            main_greenlets = start_services(
                main_services,
                start=pool.start,
                link_exception_callback=handle_greenlet_exception,
            )
            gevent.joinall(webservice_greenlets + main_greenlets)
    except Exception as exception:
        logger.exception("Application error", exc_info=exception)
        stop(pool, APPLICATION_CLEANUP_TIMEOUT)
