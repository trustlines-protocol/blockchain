from gevent import monkey

monkey.patch_all()  # noqa: E402

import logging

import gevent
from gevent import Greenlet
from gevent.queue import Queue

import click
from toml.decoder import TomlDecodeError

from web3 import Web3, HTTPProvider

from bridge.config import load_config
from bridge.event_fetcher import EventFetcher


@click.command()
@click.option(
    "-c",
    "--config",
    "config_path",
    type=click.Path(exists=True),
    default=None,
    help="Path to a config file",
)
def main(config_path: str) -> None:
    logging.basicConfig(level=logging.INFO)

    try:
        config = load_config(config_path)
    except TomlDecodeError as decode_error:
        raise click.UsageError(f"Invalid config file: {decode_error}") from decode_error
    except ValueError as value_error:
        raise click.UsageError(f"Invalid config file: {value_error}") from value_error

    w3_foreign = Web3(HTTPProvider(config["foreign_rpc_url"]))
    # w3_home = Web3(HTTPProvider(config["home_rpc_url"]))

    transfer_event_queue = Queue()

    transfer_event_fetcher = EventFetcher(
        web3=w3_foreign,
        contract_address=config["token_contract_address"],
        event_signature_hash=Web3.keccak(text="Transfer(address,address,uint256)"),
        event_argument_filter=[
            None,
            f"0x000000000000000000000000{config['foreign_bridge_contract_address'][2:]}",
        ],
        event_queue=transfer_event_queue,
        max_reorg_depth=config["foreign_chain_max_reorg_depth"],
    )

    try:
        transfer_event_fetcher_greenlet = Greenlet.spawn(
            transfer_event_fetcher.fetch_events, config["transfer_event_poll_interval"]
        )

        gevent.joinall([transfer_event_fetcher_greenlet], raise_error=True)
    finally:
        transfer_event_fetcher_greenlet.kill()
