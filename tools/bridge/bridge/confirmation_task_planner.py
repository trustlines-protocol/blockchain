from typing import Dict, List, Set

from eth_typing import Hash32
from eth_utils import decode_hex
from web3.datastructures import AttributeDict

from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
)


class TransferRecorder:
    def __init__(self, sync_persistence_time: float) -> None:
        if sync_persistence_time < 0:
            raise ValueError("Sync persistence time must not be negative")
        self.sync_persistence_time = sync_persistence_time

        self.transfer_events: Dict[Hash32, AttributeDict] = {}

        self.transfer_hashes: Set[Hash32] = set()
        self.confirmation_hashes: Set[Hash32] = set()
        self.completion_hashes: Set[Hash32] = set()

        self.scheduled_hashes: Set[Hash32] = set()

        self.confirmations_synced_until = 0.0
        self.completions_synced_until = 0.0

    def apply_sync_completed(self, event_name: str, timestamp: float) -> None:
        if event_name == TRANSFER_EVENT_NAME:
            pass
        elif event_name == CONFIRMATION_EVENT_NAME:
            if timestamp < self.confirmations_synced_until:
                raise ValueError("Sync time must never decrease")
            self.confirmations_synced_until = timestamp
        elif event_name == COMPLETION_EVENT_NAME:
            if timestamp < self.completions_synced_until:
                raise ValueError("Sync time must never decrease")
            self.completions_synced_until = timestamp
        else:
            raise ValueError(f"Got unknown event {event_name}")

    def apply_event(self, event: AttributeDict) -> None:
        event_name = event.event
        transfer_hash = Hash32(decode_hex(event.args.transferHash))
        assert len(transfer_hash) == 32

        if event_name == TRANSFER_EVENT_NAME:
            self.transfer_hashes.add(transfer_hash)
            self.transfer_events[transfer_hash] = event
        elif event_name == CONFIRMATION_EVENT_NAME:
            self.confirmation_hashes.add(transfer_hash)
        elif event_name == COMPLETION_EVENT_NAME:
            self.completion_hashes.add(transfer_hash)
        else:
            raise ValueError(f"Got unknown event {event}")

    def is_in_sync(self, current_time: float) -> bool:
        synced_until = min(
            self.confirmations_synced_until, self.completions_synced_until
        )
        return current_time <= synced_until + self.sync_persistence_time

    def clear_transfers(self) -> None:
        all_stages_seen = (
            self.transfer_hashes & self.confirmation_hashes & self.completion_hashes
        )
        self.transfer_hashes -= all_stages_seen
        self.confirmation_hashes -= all_stages_seen
        self.completion_hashes -= all_stages_seen

        self.scheduled_hashes -= all_stages_seen

        for transfer_hash in all_stages_seen:
            self.transfer_events.pop(transfer_hash, None)

    def pull_transfers_to_confirm(self, current_time: float) -> List[AttributeDict]:
        if not self.is_in_sync(current_time):
            return []
        else:
            unconfirmed_transfer_hashes = (
                self.transfer_hashes
                - self.confirmation_hashes
                - self.completion_hashes
                - self.scheduled_hashes
            )
            self.scheduled_hashes |= unconfirmed_transfer_hashes
            return [
                self.transfer_events[transfer_hash]
                for transfer_hash in unconfirmed_transfer_hashes
            ]
