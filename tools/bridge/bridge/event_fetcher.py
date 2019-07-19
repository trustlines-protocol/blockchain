import logging
import gevent

from gevent.queue import Queue
from web3 import Web3


TRANSFER_EVENT_SIGNATURE_HASH = Web3.keccak(text="Transfer(address,address,uint256)")


class TransferFetcher:
    def __init__(
        self,
        *,
        queue: Queue,
        w3_foreign: Web3,
        token_contract_address: str,
        foreign_bridge_contract_address: str,
        foreign_chain_max_reorg_depth: int,
        transfer_event_fetch_limit: int,
    ):
        token_contract_code = w3_foreign.eth.getCode(token_contract_address)

        if not token_contract_code:
            raise ValueError(
                f"The given token contract address {token_contract_address} "
                "does not point to a contract!"
            )

        if TRANSFER_EVENT_SIGNATURE_HASH not in token_contract_code:
            raise ValueError(
                f"The token contract at the given address {token_contract_address}"
                "does not have the (correct) 'Transfer' event!"
            )

        foreign_bridge_contract_code = w3_foreign.eth.getCode(
            foreign_bridge_contract_address
        )

        if not foreign_bridge_contract_code:
            raise ValueError(
                f"The given foreign bridge contract address {foreign_bridge_contract_address} "
                "does not point to a contract!"
            )

        self._logger = logging.getLogger("bridge.transfer_fetcher")
        self._w3_foreign = w3_foreign
        self._queue = queue
        self._token_contract_address = token_contract_address
        self._foreign_bridge_contract_address = foreign_bridge_contract_address
        self._foreign_chain_max_reorg_depth = foreign_chain_max_reorg_depth
        self._transfer_event_fetch_limit = transfer_event_fetch_limit
        self._last_fetched_block_number = (
            -1
        )  # Fetching starts always one block after the last one.

    def _fetch_token_transfer_events_in_range(
        self, from_block_number: int, to_block_number: int
    ) -> None:
        from_block_number = max(from_block_number, 0)
        to_block_number = min(to_block_number, self._w3_foreign.eth.blockNumber)

        self._logger.debug(
            "Fetch transfer events from block {from_block_number} to {to_block_number}."
        )

        assert from_block_number <= to_block_number, (
            f"Can not fetch from a negative range of blocks "
            f"({from_block_number} to {to_block_number})"
        )

        events = self._w3_foreign.eth.getLogs(
            {
                "fromBlock": from_block_number,
                "toBlock": to_block_number,
                "address": self._token_contract_address,
                "topics": [
                    TRANSFER_EVENT_SIGNATURE_HASH.hex(),
                    None,
                    f"0x000000000000000000000000{self._foreign_bridge_contract_address[2:]}",
                ],
            }
        )

        self._logger.debug(f"Found {len(events)} events.")

        for event in events:
            self._queue.put(event)

    def _fetch_token_transfer_events_not_seen(self) -> None:
        self._logger.debug("Fetch new transfer events.")
        self._logger.debug(
            f"Last fetched block number: {self._last_fetched_block_number}."
        )

        head_block_number = max(
            self._w3_foreign.eth.blockNumber - self._foreign_chain_max_reorg_depth, 0
        )

        self._logger.debug(
            f"Fetch to new head {head_block_number} respecting "
            f"the maximum reorg depth of {self._foreign_chain_max_reorg_depth}."
        )

        for from_block_number in range(
            self._last_fetched_block_number + 1,
            head_block_number + 1,
            self._transfer_event_fetch_limit,
        ):
            to_block_number = min(
                from_block_number + self._transfer_event_fetch_limit - 1,
                head_block_number,
            )

            self._fetch_token_transfer_events_in_range(
                from_block_number, to_block_number
            )

        self._last_fetched_block_number = head_block_number

    def fetch_token_transfer_events(self, transfer_event_poll_interval: int) -> None:
        self._logger.debug("Start token transfer fetcher.")

        while True:
            self._fetch_token_transfer_events_not_seen()
            gevent.sleep(transfer_event_poll_interval)
