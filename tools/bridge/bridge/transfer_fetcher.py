import logging

import gevent
from gevent.queue import Queue

from web3 import Web3


def fetch_transfer_events(
    w3_foreign: Web3, transfer_event_queue: Queue, poll_interval: int
) -> None:
    logger = logging.getLogger("bridge.transfer_fetcher.fetch_transfer_events")

    last_block_number = None
    while True:
        logger.debug("Fetching new transfer events")

        # use block number as a placeholder until we get actual events
        current_block_number = w3_foreign.eth.blockNumber
        if current_block_number != last_block_number:
            logger.info(f"fetched new transfer: {current_block_number}")
            transfer_event_queue.put(current_block_number)
            last_block_number = current_block_number

        gevent.sleep(poll_interval)
