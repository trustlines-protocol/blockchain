import logging
import operator
from time import sleep
from typing import Any, Dict, List, Optional

import attr
from eth_utils import to_checksum_address
from eth_utils.toolz import groupby
from gevent.queue import Queue
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict


@attr.s
class EventBatch:
    timestamp: int = attr.ib()
    events: List[AttributeDict] = attr.ib()


class EventFetcher:
    def __init__(
        self,
        *,
        web3: Web3,
        contract: Contract,
        event_name: str,
        event_argument_filter: Dict[str, Any],
        event_fetch_limit: int = 950,
        event_batch_queue: Queue,
        max_reorg_depth: int,
        start_block_number: int,
    ):
        if event_fetch_limit <= 0:
            raise ValueError("Can not fetch events with zero or negative limit!")

        if max_reorg_depth < 0:
            raise ValueError("Invalid maximum reorg depth with a negative value!")

        if start_block_number < 0:
            raise ValueError(
                "Can not fetch events starting from a negative block number!"
            )

        self.logger = logging.getLogger(
            f"bridge.event_fetcher.{to_checksum_address(contract.address)}.{event_name}"
        )

        self.web3 = web3
        self.contract = contract
        self.event_name = event_name
        self.event_argument_filter = event_argument_filter
        self.event_fetch_limit = event_fetch_limit
        self.event_batch_queue = event_batch_queue
        self.max_reorg_depth = max_reorg_depth
        self.last_fetched_block_number = start_block_number - 1

    def fetch_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> List[AttributeDict]:
        if from_block_number < 0:
            raise ValueError("Can not fetch events from a negative block number!")

        if to_block_number > self.web3.eth.blockNumber:
            raise ValueError("Can not fetch events for blocks past the current head!")

        if from_block_number > to_block_number:
            raise ValueError("Can not fetch events for a negative range!")

        self.logger.debug(
            f"Fetch events from block {from_block_number} to {to_block_number}."
        )

        events = self.contract.events[self.event_name].getLogs(
            fromBlock=from_block_number,
            toBlock=to_block_number,
            argument_filters=self.event_argument_filter,
        )

        if len(events) > 0:
            self.logger.info(f"Found {len(events)} events.")
        else:
            self.logger.debug(f"Found {len(events)} events.")

        return events

    def fetch_some_event_batches(self) -> Optional[List[EventBatch]]:
        """Fetch some event batches starting from the last_fetched_block_number

        This method tries to fetch from consecutive ranges of blocks
        until it has found some events in a range of blocks or it has
        reached the head of the chain.

        This method returns None if the caller should wait for new blocks to
        come in.
        """
        from_block_number = self.last_fetched_block_number + 1
        reorg_safe_block_number = self.web3.eth.blockNumber - self.max_reorg_depth
        to_block_number = min(
            from_block_number + self.event_fetch_limit - 1, reorg_safe_block_number
        )

        if to_block_number < from_block_number:
            return None
        else:
            events = self.fetch_events_in_range(from_block_number, to_block_number)
            self.last_fetched_block_number = to_block_number

            if events:
                events_by_block_hash = groupby(operator.attrgetter("blockHash"), events)
                timestamps_by_block_hash = {
                    block_hash: self.web3.eth.getBlock(block_hash).timestamp
                    for block_hash in events_by_block_hash.keys()
                }
                unsorted_batches = [
                    EventBatch(
                        timestamp=timestamps_by_block_hash[block_hash],
                        events=events_by_block_hash[block_hash],
                    )
                    for block_hash in events_by_block_hash
                ]
                batches = sorted(unsorted_batches, key=operator.attrgetter("timestamp"))
            else:
                to_block = self.web3.eth.getBlock(to_block_number)
                to_block_timestamp = to_block.timestamp
                empty_batch = EventBatch(timestamp=to_block_timestamp, events=[])
                batches = [empty_batch]

            return batches

    def fetch_events(self, poll_interval: int) -> None:
        if poll_interval <= 0:
            raise ValueError(
                "Can not fetch events with a zero or negative poll interval!"
            )

        self.logger.debug("Start event fetcher.")

        while True:
            event_batches = self.fetch_some_event_batches()
            if event_batches is not None:
                for event_batch in event_batches:
                    self.event_batch_queue.put(event_batch)
            else:
                sleep(poll_interval)
