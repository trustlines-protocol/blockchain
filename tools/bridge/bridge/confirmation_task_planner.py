from typing import List, Set, NamedTuple, Optional

import gevent
from gevent.queue import Queue

from eth_typing import Hash32

from eth_utils import decode_hex


class TimestampedTransferHash(NamedTuple):
    timestamp: int
    transfer_hash: Hash32


class TransferHashRecorder:
    def __init__(self) -> None:
        self.timestamped_transfer_hashes: List[TimestampedTransferHash] = []
        self.current_timestamp = 0

    def record_transfer_hash(
        self, timestamp: int, transfer_hash: Optional[Hash32]
    ) -> None:
        """Record an event or record that no further event happened until the given timestamp.

        Events or non-events must be recorded in order.
        """
        if timestamp < self.current_timestamp:
            raise ValueError(f"Tried to apply event out of order")
        self.current_timestamp = timestamp

        if transfer_hash is not None:
            timestamped_transfer_hash = TimestampedTransferHash(
                timestamp, transfer_hash
            )
            self.timestamped_transfer_hashes.append(timestamped_transfer_hash)

    def forget_transfer_hash(self, transfer_hash: Hash32) -> None:
        """Drop a specific transfer hash."""
        self.timestamped_transfer_hashes = [
            timestamped_transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
            if timestamped_transfer_hash.transfer_hash != transfer_hash
        ]

    def forget_old_transfer_hashes(self, cutoff_timestamp: int) -> None:
        """Drop all transfer hashes that happened before the given cutoff timestamp."""
        self.timestamped_transfer_hashes = [
            timestamped_transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
            if timestamped_transfer_hash.timestamp >= cutoff_timestamp
        ]

    def transfer_hash_exists(self, transfer_hash: Hash32) -> bool:
        """Check if a transfer hash has been recorded and not yet forgotten or not."""
        return any(
            timestamped_transfer_hash.transfer_hash == transfer_hash
            for timestamped_transfer_hash in self.timestamped_transfer_hashes
        )

    def get_transfer_hashes(self, start_time: int, end_time: int) -> List[Hash32]:
        """Return all transfer hashes in a given (inclusive) time interval."""
        return [
            transfer_hash
            for timestamp, transfer_hash in self.timestamped_transfer_hashes
            if start_time <= timestamp <= end_time
        ]


class TransferHashCollector:
    def __init__(self, home_look_ahead: int, history_length: int) -> None:
        self.transfer_event_recorder = TransferHashRecorder()
        self.confirmation_event_recorder = TransferHashRecorder()
        self.completion_event_recorder = TransferHashRecorder()

        self.recently_processed_transfer_hashes: Set[Hash32] = set()

        self.home_look_ahead = home_look_ahead
        self.history_length = history_length

        self.transfers_processed_until = 0

    def apply_transfer_hash(
        self, event: str, timestamp: int, transfer_hash: Optional[Hash32]
    ) -> None:
        if event == "Transfer":
            recorder = self.transfer_event_recorder
        elif event == "Confirmation":
            recorder = self.confirmation_event_recorder
        elif event == "Completion":
            recorder = self.completion_event_recorder
        else:
            raise ValueError("Got unknown event {event}")

        recorder.record_transfer_hash(timestamp, transfer_hash)

    def get_next_transfer_hashes(self) -> List[Hash32]:
        transfer_time = self.transfer_event_recorder.current_timestamp
        confirmation_time = self.confirmation_event_recorder.current_timestamp
        completion_time = self.completion_event_recorder.current_timestamp

        home_time = min(confirmation_time, completion_time)

        start_time = self.transfers_processed_until
        end_time = min(home_time - self.home_look_ahead, transfer_time)

        transfer_hashes = self.transfer_event_recorder.get_transfer_hashes(
            start_time=start_time, end_time=end_time
        )
        self.transfers_processed_until = transfer_time

        new_transfer_hashes = []
        for transfer_hash in transfer_hashes:
            recently_processed = (
                transfer_hash in self.recently_processed_transfer_hashes
            )
            already_confirmed = self.confirmation_event_recorder.transfer_hash_exists(
                transfer_hash
            )
            already_completed = self.completion_event_recorder.transfer_hash_exists(
                transfer_hash
            )

            if (
                not recently_processed
                and not already_confirmed
                and not already_completed
            ):
                new_transfer_hashes.append(transfer_hash)
                self.recently_processed_transfer_hashes.add(transfer_hash)

        return new_transfer_hashes

    def clear_history(self):
        cutoff_time = (
            min(
                self.transfer_event_recorder.current_timestamp,
                self.confirmation_event_recorder.current_timestamp,
                self.completion_event_recorder.current_timestamp,
            )
            - self.history_length
        )

        self.transfer_event_recorder.forget_old_transfer_hashes(cutoff_time)
        self.confirmation_event_recorder.forget_old_transfer_hashes(cutoff_time)
        self.completion_event_recorder.forget_old_transfer_hashes(cutoff_time)

        cleared_transfer_hashes = set(
            transfer_hash
            for transfer_hash in self.recently_processed_transfer_hashes
            if not self.transfer_event_recorder.transfer_hash_exists(transfer_hash)
        )
        processed_transfer_hashes = set(
            transfer_hash
            for transfer_hash in self.recently_processed_transfer_hashes
            if all(
                self.transfer_event_recorder.transfer_hash_exists(transfer_hash),
                self.confirmation_event_recorder.transfer_hash_exists(transfer_hash),
                self.completion_event_recorder.transfer_hash_exists(transfer_hash),
            )
        )
        self.recently_processed_transfer_hashes -= cleared_transfer_hashes
        self.recently_processed_transfer_hashes -= processed_transfer_hashes


class ConfirmationTaskPlanner:
    def __init__(
        self,
        transfer_event_queue: Queue,
        confirmation_event_queue: Queue,
        completion_event_queue: Queue,
        confirmation_task_queue: Queue,
        home_look_ahead: int,
        history_length: int,
    ) -> None:
        self.transfer_event_queue = transfer_event_queue
        self.confirmation_event_queue = confirmation_event_queue
        self.completion_event_queue = completion_event_queue

        self.confirmation_task_queue = confirmation_task_queue

        self.collector = TransferHashCollector(home_look_ahead, history_length)

    def run(self) -> None:
        try:
            greenlets = [
                gevent.run(self.process_events, self.transfer_event_queue),
                gevent.run(self.process_events, self.confirmation_event_queue),
                gevent.run(self.process_events, self.completion_event_queue),
            ]
        finally:
            for greenlet in greenlets:
                gevent.kill(greenlet)

    def process_events(self, queue: Queue) -> None:
        while True:
            event = queue.get()
            self.apply_event(event)
            for transfer_hash in self.collector.get_next_transfer_hashes():
                self.confirmation_task_queue.put(transfer_hash)
            self.collector.clear_history()

    def apply_event(self, event: dict) -> None:
        # TODO: handle artificial events
        event_name = event["event"]
        if event_name not in ("Transfer", "Confirmation", "Completion"):
            raise ValueError(f"Got unknown event {event_name}")

        timestamp = 0  # TODO: get timestamp from queue
        transfer_hash = Hash32(decode_hex(event["args"]["transferHash"]))
        self.collector.apply_transfer_hash(event_name, timestamp, transfer_hash)
