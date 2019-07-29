from typing import List, Set

from eth_typing import Hash32


MAX_CLOCK_DISPARITY = 60  # maximum lock disparity between home and foreign chain
HISTORY_TIME = 60 * 60  # forget about events that are older than this time


class TimestampedTransferHash:
    timestamp: int
    transfer_hash: Hash32


class TransferHashRecorder:
    def __init__(self):
        self.timestamped_transfer_hashes: List[TimestampedTransferHash] = []
        self.current_timestamp = 0

    def apply_event_batch(self, timestamp, events):
        if timestamp < self.current_timestamp:
            raise ValueError(f"Tried to apply events out of order")
        self.current_timestamp = timestamp

        for event in events:
            timestamped_transfer_hash = TimestampedTransferHash(
                timestamp, events.args.transferHash
            )
            self.timestamped_transfer_hashes.append(timestamped_transfer_hash)

    def forget_transfer_hash(self, transfer_hash: Hash32) -> None:
        self.timestamped_transfer_hashes = [
            timestamped_transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
            if timestamped_transfer_hash.transfer_hash != transfer_hash
        ]

    def forget_old_transfer_hashes(self, cutoff_timestamp: int) -> None:
        self.timestamped_transfer_hashes = [
            timestamped_transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
            if timestamped_transfer_hash.timestamp < cutoff_timestamp
        ]

    def transfer_hash_exists(self, transfer_hash: Hash32) -> bool:
        return any(
            timestamped_transfer_hash.transfer_hash == transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
        )


class ConfirmationTaskPlanner:
    def __init__(self):
        self.transfer_event_recorder = TransferHashRecorder()
        self.confirmation_event_recorder = TransferHashRecorder()
        self.completion_event_recorder = TransferHashRecorder()

        self.recently_handled_transfer_hashes: Set[TimestampedTransferHash] = set()

    def get_next_transfers_to_confirm(self) -> List[Hash32]:
        transfer_hashes_to_confirm = []

        for (
            timestamped_transfer_hash
        ) in self.transfer_event_recorder.timestamped_transfer_hashes:
            timestamp, transfer_hash = timestamped_transfer_hash

            # stop if home chain syning isn't sufficiently far yet
            if (
                timestamp
                > self.confirmation_event_recorder.current_timestamp
                - MAX_CLOCK_DISPARITY
            ):
                break
            if (
                timestamp
                > self.completion_event_recorder.current_timestamp - MAX_CLOCK_DISPARITY
            ):
                break

            # ignore this transfer if we've handled it already
            if transfer_hash in self.recently_handled_transfer_hashes:
                continue

            # check if we need to confirm it
            already_confirmed = self.confirmation_event_recorder.transfer_hash_exists(
                transfer_hash
            )
            already_completed = self.completion_event_recorder.transfer_hash_exists(
                transfer_hash
            )

            if already_confirmed or already_completed:
                self.recently_handled_transfer_hashes.add(timestamped_transfer_hash)
                transfer_hashes_to_confirm.append(transfer_hash)

        return transfer_hashes_to_confirm

    def clear_history(self):
        cutoff_time = (
            min(
                self.transfer_event_recorder.current_timestamp,
                self.confirmation_event_recorder.current_timestamp,
                self.completion_event_recorder.current_timestamp,
            )
            - HISTORY_TIME
        )
        transfer_hashes_to_clear = set(
            transfer_hash
            for transfer_hash, timestamp in self.recently_handled_transfer_hashes
            if timestamp < cutoff_time
        )
        self.recently_handled_transfer_hashes -= transfer_hashes_to_clear

        self.transfer_event_recorder.forget_old_transfer_hashes(cutoff_time)
        self.confirmation_event_recorder.forget_old_transfer_hashes(cutoff_time)
        self.completion_event_recorder.forget_old_transfer_hashes(cutoff_time)

    def apply_transfer_event_batch(self, timestamp, events):
        self.transfer_event_recorder.apply_event_batch(timestamp, events)
        transfer_hashes_to_confirm = self.get_next_transfers_to_confirm()
        self.clear_history()
        return transfer_hashes_to_confirm

    def apply_confirmation_event_batch(self, timestamp, events):
        self.confirmation_event_recorder.apply_event_batch(timestamp, events)
        transfer_hashes_to_confirm = self.get_next_transfers_to_confirm()
        self.clear_history()
        return transfer_hashes_to_confirm

    def apply_completion_event_batch(self, timestamp, events):
        self.completion_event_recorder.apply_event_batch(timestamp, events)
        transfer_hashes_to_confirm = self.get_next_transfers_to_confirm()
        self.clear_history()
        return transfer_hashes_to_confirm
