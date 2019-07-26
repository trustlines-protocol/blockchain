import logging

from typing import Dict, Any
from time import sleep
from web3 import Web3
from web3.contract import Contract


class EventFetcher:
    def __init__(
        self,
        *,
        web3: Web3,
        contract: Contract,
        event_name: str,
        event_argument_filter: Dict[str, Any],
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
            f"bridge.event_fetcher.{contract.address}.{event_name}"
        )

        self.web3 = web3
        self.contract = contract
        self.event_name = event_name
        self.event_argument_filter = event_argument_filter
        self.event_fetch_limit = event_fetch_limit
        self.event_queue = event_queue
        self.max_reorg_depth = max_reorg_depth
        self.last_fetched_block_number = start_block_number

    def fetch_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> None:
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

        for event in events:
            self.event_queue.put(event)

    def fetch_events_not_seen(self) -> None:
        self.logger.debug("Fetch new events.")
        self.logger.debug(
            f"Last fetched block number: {self.last_fetched_block_number}."
        )

        fetch_until_block_number = max(
            self.web3.eth.blockNumber - self.max_reorg_depth, 0
        )

        self.logger.debug(
            f"Fetch until {fetch_until_block_number} respecting "
            f"the maximum reorg depth of {self.max_reorg_depth}."
        )

        for from_block_number in range(
            self.last_fetched_block_number + 1,
            fetch_until_block_number + 1,
            self.event_fetch_limit,
        ):
            to_block_number = min(
                from_block_number + self.event_fetch_limit - 1, fetch_until_block_number
            )

            self.fetch_events_in_range(from_block_number, to_block_number)

        self.last_fetched_block_number = fetch_until_block_number

    def fetch_events(self, poll_interval: int) -> None:
        if poll_interval <= 0:
            raise ValueError(
                "Can not fetch events with a zero or negative poll interval!"
            )

        self.logger.debug("Start event fetcher.")

        while True:
            self.fetch_events_not_seen()
            sleep(poll_interval)
