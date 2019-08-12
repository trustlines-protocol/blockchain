from typing import Dict, List, Set

from eth_typing import Hash32
from web3.datastructures import AttributeDict

from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
)
from bridge.utils import compute_transfer_hash


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

        self.home_chain_synced_until = 0.0

    def apply_home_chain_synced_event(self, timestamp: float) -> None:
        if timestamp < self.home_chain_synced_until:
            raise ValueError("Sync time must not decrease")
        self.home_chain_synced_until = timestamp

    def apply_proper_event(self, event: AttributeDict) -> None:
        event_name = event.event

        if event_name == TRANSFER_EVENT_NAME:
            transfer_hash = compute_transfer_hash(event)
            self.transfer_hashes.add(transfer_hash)
            self.transfer_events[transfer_hash] = event
        elif event_name == CONFIRMATION_EVENT_NAME:
            transfer_hash = Hash32(bytes(event.args.transferHash))
            assert len(transfer_hash) == 32
            self.confirmation_hashes.add(transfer_hash)
        elif event_name == COMPLETION_EVENT_NAME:
            transfer_hash = Hash32(bytes(event.args.transferHash))
            assert len(transfer_hash) == 32
            self.completion_hashes.add(transfer_hash)
        else:
            raise ValueError(f"Got unknown event {event}")

    def is_in_sync(self, current_time: float) -> bool:
        return current_time <= self.home_chain_synced_until + self.sync_persistence_time

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
            confirmation_tasks: List[AttributeDict] = []
        else:
            unconfirmed_transfer_hashes = (
                self.transfer_hashes
                - self.confirmation_hashes
                - self.completion_hashes
                - self.scheduled_hashes
            )
            self.scheduled_hashes |= unconfirmed_transfer_hashes
            confirmation_tasks = [
                self.transfer_events[transfer_hash]
                for transfer_hash in unconfirmed_transfer_hashes
            ]

        self.clear_transfers()
        return confirmation_tasks
