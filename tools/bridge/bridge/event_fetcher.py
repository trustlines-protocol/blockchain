import logging
from time import sleep, time
from typing import Any, Dict, List

from eth_utils import to_checksum_address
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict


class FetcherReachedHeadEvent:
    def __init__(self):
        self.timestamp = int(time())


class EventFetcher:
    def __init__(
        self,
        *,
        web3: Web3,
        contract: Contract,
        filter_definition: Dict[str, Dict[str, Any]],
        event_fetch_limit: int = 950,
        event_queue: Any,
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
            f"bridge.event_fetcher.{to_checksum_address(contract.address)}"
        )

        self.web3 = web3
        self.contract = contract
        self.filter_definition = filter_definition
        self.event_fetch_limit = event_fetch_limit
        self.event_queue = event_queue
        self.max_reorg_depth = max_reorg_depth
        self.last_fetched_block_number = start_block_number - 1

    def fetch_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> List:
        if from_block_number < 0:
            raise ValueError("Can not fetch events from a negative block number!")

        if to_block_number > self.web3.eth.blockNumber:
            raise ValueError("Can not fetch events for blocks past the current head!")

        if from_block_number > to_block_number:
            raise ValueError("Can not fetch events for a negative range!")

        self.logger.debug(
            f"Fetch events from block {from_block_number} to {to_block_number}."
        )

        events: List[AttributeDict] = []
        for event_name, argument_filters in self.filter_definition.items():
            events.extend(
                self.contract.events[event_name].getLogs(
                    fromBlock=from_block_number,
                    toBlock=to_block_number,
                    argument_filters=argument_filters,
                )
            )
        events.sort(
            key=lambda event: (
                event.blockNumber,
                event.transactionIndex,
                event.logIndex,
            )
        )

        if len(events) > 0:
            self.logger.info(f"Found {len(events)} events.")
        else:
            self.logger.debug(f"Found {len(events)} events.")

        return events

    def fetch_some_events(self) -> List:
        """fetch some events starting from the last_fetched_block_number

        This method tries to fetch from consecutive ranges of blocks
        until it has found some events in a range of blocks or it has
        reached the head of the chain.

        This method returns an empty list if the caller should wait
        for new blocks to come in.
        """
        while True:
            from_block_number = self.last_fetched_block_number + 1
            reorg_safe_block_number = self.web3.eth.blockNumber - self.max_reorg_depth
            to_block_number = min(
                from_block_number + self.event_fetch_limit - 1, reorg_safe_block_number
            )
            if to_block_number < from_block_number:
                return []
            events = self.fetch_events_in_range(from_block_number, to_block_number)
            self.last_fetched_block_number = to_block_number
            if events:
                return events

    def fetch_events(self, poll_interval: int) -> None:
        if poll_interval <= 0:
            raise ValueError(
                "Can not fetch events with a zero or negative poll interval!"
            )

        self.logger.debug("Start event fetcher.")

        while True:
            events = self.fetch_some_events()
            for event in events:
                self.event_queue.put(event)

            if not events:
                self.event_queue.put(FetcherReachedHeadEvent())
                sleep(poll_interval)
