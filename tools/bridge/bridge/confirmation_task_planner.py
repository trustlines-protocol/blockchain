from typing import List, Set

from eth_typing import Hash32

TRANSFER_EVENT_NAME = "Transfer"
CONFIRMATION_EVENT_NAME = "Confirmation"
COMPLETION_EVENT_NAME = "TransferCompleted"


class ConfirmationTaskPlanner:
    def __init__(self, sync_persistence_time: int) -> None:
        self.sync_persistence_time = sync_persistence_time

        self.transfer_hashes: Set[Hash32] = set()
        self.confirmation_hashes: Set[Hash32] = set()
        self.completion_hashes: Set[Hash32] = set()

        self.scheduled_hashes: Set[Hash32] = set()

        self.confirmations_synced_until = 0.0
        self.completions_synced_until = 0.0

    def apply_sync_completed(self, event: str, timestamp: float) -> None:
        if event == TRANSFER_EVENT_NAME:
            pass
        elif event == CONFIRMATION_EVENT_NAME:
            if timestamp < self.confirmations_synced_until:
                raise ValueError("Sync time must never decrease")
            self.confirmations_synced_until = timestamp
        elif event == COMPLETION_EVENT_NAME:
            if timestamp < self.completions_synced_until:
                raise ValueError("Sync time must never decrease")
            self.completions_synced_until = timestamp
        else:
            raise ValueError(f"Got unknown event {event}")

    def apply_transfer_hash(self, event: str, transfer_hash: Hash32) -> None:
        if event == TRANSFER_EVENT_NAME:
            self.transfer_hashes.add(transfer_hash)
        elif event == CONFIRMATION_EVENT_NAME:
            self.confirmation_hashes.add(transfer_hash)
        elif event == COMPLETION_EVENT_NAME:
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
        self.scheduled_hashes -= all_stages_seen

    def get_next_transfer_hashes(self, current_time: int) -> Set[Hash32]:
        if not self.is_in_sync(current_time):
            return set()
        else:
            transfers_to_confirm = (
                self.transfer_hashes
                - self.confirmation_hashes
                - self.completion_hashes
                - self.scheduled_hashes
            )
            self.scheduled_hashes |= transfers_to_confirm
            return transfers_to_confirm
