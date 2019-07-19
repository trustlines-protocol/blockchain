import logging
import gevent

from typing import List
from gevent.queue import Queue
from web3 import Web3
from hexbytes import HexBytes


class EventFetcher:
    def __init__(
        self,
        *,
        web3: Web3,
        contract_address: str,
        event_signature_hash: HexBytes,
        event_argument_filter: List,
        event_fetch_limit: int = 950,
        event_queue: Queue,
        max_reorg_depth: int,
    ):
        contract_code = web3.eth.getCode(contract_address)

        if not contract_code:
            raise ValueError(
                f"The given contract address {contract_address} does not point to a contract!"
            )

        if event_signature_hash not in contract_code:
            raise ValueError(
                f"The contract at the given address {contract_address}"
                "does not have an event with the given signature!"
            )

        assert event_fetch_limit > 0
        assert max_reorg_depth > 0

        self.logger = logging.getLogger(
            f"bridge.event_fetcher.{contract_address}.{event_signature_hash}"
        )

        self.web3 = web3
        self.contract_address = contract_address
        self.event_signature_hash = event_signature_hash
        self.event_argument_filter = event_argument_filter
        self.event_fetch_limit = event_fetch_limit
        self.event_queue = event_queue
        self.max_reorg_depth = max_reorg_depth

        # Fetching starts always one block after the last one.
        self.last_fetched_block_number = -1

    def fetch_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> None:
        from_block_number = max(from_block_number, 0)
        to_block_number = min(to_block_number, self.web3.eth.blockNumber)

        self.logger.debug(
            f"Fetch events from block {from_block_number} to {to_block_number}."
        )

        assert from_block_number <= to_block_number, (
            f"Can not fetch from a negative range of blocks "
            f"({from_block_number} to {to_block_number})"
        )

        events = self.web3.eth.getLogs(
            {
                "fromBlock": from_block_number,
                "toBlock": to_block_number,
                "address": self.contract_address,
                "topics": [self.event_signature_hash.hex()]
                + self.event_argument_filter,
            }
        )

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
        assert poll_interval > 0

        self.logger.debug("Start event fetcher.")

        while True:
            self.fetch_events_not_seen()
            gevent.sleep(poll_interval)
