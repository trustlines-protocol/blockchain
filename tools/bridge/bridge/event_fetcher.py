import logging
import time
from typing import Any, Dict, List

import tenacity
from web3 import Web3
from web3.contract import Contract
from web3.datastructures import AttributeDict

from bridge import node_status
from bridge.events import ChainRole, FetcherReachedHeadEvent
from bridge.utils import sort_events

NODE_STATUS_CACHE_TIME_SECONDS = 1


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
        chain_role: ChainRole,
    ):
        if event_fetch_limit <= 0:
            raise ValueError("Can not fetch events with zero or negative limit!")

        if max_reorg_depth < 0:
            raise ValueError("Invalid maximum reorg depth with a negative value!")

        if start_block_number < 0:
            raise ValueError(
                "Can not fetch events starting from a negative block number!"
            )
        self.chain_role = chain_role
        self.logger = logging.getLogger(f"{__name__}.{chain_role.name}")

        self.web3 = web3
        self.contract = contract
        self.filter_definition = filter_definition
        self.event_fetch_limit = event_fetch_limit
        self.event_queue = event_queue
        self.max_reorg_depth = max_reorg_depth
        self.last_fetched_block_number = start_block_number - 1

        self._node_status = None

        # We can't use the tenacity decorator because we're using an
        # instance local logger So, we instantiate the Retrying object
        # here and use it explicitly.
        self._retrying = tenacity.Retrying(
            wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
            before_sleep=tenacity.before_sleep_log(self.logger, logging.WARN),
        )

    def _rpc_get_cached_node_status(self):
        if (
            self._node_status is None
            or time.time() - self._node_status.timestamp
            > NODE_STATUS_CACHE_TIME_SECONDS
        ):
            # To reduce number of node calls we cache the result
            self._node_status = self._retrying.call(
                node_status.get_node_status, self.web3
            )
        return self._node_status

    def _rpc_cached_latest_block(self):
        return self._rpc_get_cached_node_status().latest_synced_block

    def _rpc_cached_is_syncing(self):
        return self._rpc_get_cached_node_status().is_syncing

    def _rpc_get_logs(
        self,
        event_name: str,
        from_block_number: int,
        to_block_number: int,
        argument_filters,
    ):
        return self._retrying.call(
            self.contract.events[event_name].getLogs,
            fromBlock=from_block_number,
            toBlock=to_block_number,
            argument_filters=argument_filters,
        )

    def fetch_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> List:
        if from_block_number < 0:
            raise ValueError("Can not fetch events from a negative block number!")

        if from_block_number > to_block_number:
            raise ValueError("Can not fetch events for a negative range!")

        self.logger.debug(
            f"Fetch events from block {from_block_number} to {to_block_number}."
        )

        events: List[AttributeDict] = []
        for event_name, argument_filters in self.filter_definition.items():
            fetched_events = self._rpc_get_logs(
                event_name=event_name,
                from_block_number=from_block_number,
                to_block_number=to_block_number,
                argument_filters=argument_filters,
            )
            events += fetched_events

            if len(fetched_events) > 0:
                self.logger.info(f"Found {len(fetched_events)} {event_name} events.")
            else:
                self.logger.debug(f"Found {len(fetched_events)} {event_name} events.")

        sort_events(events)
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
            reorg_safe_block_number = (
                self._rpc_cached_latest_block() - self.max_reorg_depth
            )
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
                # instantiate this event here in order to use the
                # current time as timestamp
                reached_head_event = FetcherReachedHeadEvent(
                    timestamp=time.time(),
                    chain_role=self.chain_role,
                    last_fetched_block_number=self.last_fetched_block_number,
                )
                if not self._rpc_cached_is_syncing():
                    self.event_queue.put(reached_head_event)
                time.sleep(poll_interval)
