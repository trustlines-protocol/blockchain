import logging
from typing import Set

from gevent.event import Event
from gevent.queue import Queue, Empty

from eth_typing import Hash32

from eth_utils import decode_hex, encode_hex

from bridge.event_fetcher import EventFetcher


class TransferHashRecorder:
    def __init__(self, event_fetcher: EventFetcher) -> None:
        self.event_fetcher = event_fetcher
        self.seen_transfer_hashes: Set[Hash32] = set()

        self.sync_status_changed = Event()
        self.is_in_sync = False

        self.logger = logging.getLogger(
            "bridge.transfer_hash_recorder.TransferHashRecorder"
        )

    def forget_transfer_hash(self, transfer_hash: Hash32) -> None:
        try:
            self.seen_transfer_hashes.remove(transfer_hash)
        except KeyError:
            pass

    def transfer_hash_exists(self, transfer_hash: Hash32) -> bool:
        return transfer_hash in self.seen_transfer_hashes

    def update_sync_status(self, now_in_sync: bool) -> None:
        if self.is_in_sync is not now_in_sync:
            self.is_in_sync = now_in_sync
            self.sync_status_changed.set()
            self.sync_status_changed.clear()

    def run(self) -> None:
        while True:
            assert not self.is_in_sync
            try:
                self.logger.debug("Getting new event")
                event = self.event_fetcher.event_queue.get(block=False)
            except Empty:
                self.logger.debug("No event available")
                if self.event_fetcher.is_in_sync:
                    # all events have been put on the fetcher's event queue and we've processed all
                    # of them, so we're fully synced as well
                    self.update_sync_status(True)

                    self.logger.debug("Waiting for event fetcher to be out of sync")
                    self.event_fetcher.sync_status_changed.wait()

                    self.update_sync_status(False)
                else:
                    # wait until the event fetcher either has a new event for us or acknowledges
                    # that we got everything
                    self.logger.debug("Waiting for event fetcher to be out of sync")
                    self.event_fetcher.sync_status_changed.wait()
            else:
                transfer_hash = Hash32(decode_hex(event.args.transferHash))
                assert len(transfer_hash) == 32
                self.logger.debug(
                    f"Recording event with hash {encode_hex(transfer_hash)}"
                )
                self.seen_transfer_hashes.add(transfer_hash)


class ConfirmationTaskPlanner:
    """Decides if we should confirm transfers or not."""

    def __init__(
        self,
        transfer_event_queue: Queue,
        confirmation_recorder: TransferHashRecorder,
        completion_recorder: TransferHashRecorder,
        transfer_task_queue: Queue,
    ):
        self.transfer_event_queue = transfer_event_queue
        self.confirmation_recorder = confirmation_recorder
        self.completion_recorder = completion_recorder

        self.logger = logging.getLogger(
            "bridge.confirmation_task_planner.ConfirmationTaskPlanner"
        )

    def run(self):
        while True:
            self.transfer_event_queue.peek()

            # wait until we've processed all transfer confirmation and completion events
            if not self.confirmation_recorder.is_in_sync:
                self.logger.debug("waiting for confirmation events")
                self.confirmation_recorder.sync_status_changed.wait()
            if not self.completion_recorder.is_in_sync:
                self.logger.debug("waiting for completion events")
                self.completion_recorder.sync_status_changed.wait()
            if (
                not self.confirmation_recorder.is_in_sync
                and self.completion_recorder.is_in_sync
            ):
                continue

            # we've peeked earlier to make sure this will never fail
            transfer = self.transfer_event_queue.get(block=False)
            self.handle_transfer(transfer)

    def handle_transfer(self, transfer):
        transfer_hash = transfer.args.transferHash
        already_confirmed = self.confirmation_recorder.transfer_hash_exists(
            transfer_hash
        )
        already_completed = self.completion_recorder.transfer_hash_exists(transfer_hash)

        if not already_confirmed and not already_completed:
            self.logger.info(f"Scheduling confirmation of transfer {transfer}")
            self.transfer_task_queue.put(transfer)
        elif already_completed:
            self.logger.info(f"Ignoring transfer {transfer} as it's already completed")
        elif already_confirmed:
            self.logger.info(
                f"Ignoring transfer {transfer} as we've already confirmed it"
            )
        else:
            assert False

        self.confirmation_recorder.forget_transfer_hash(transfer_hash)
        self.completion_recorder.forget_transfer_hash(transfer_hash)
