import logging
import time

import gevent
from gevent.queue import Queue

from bridge.event_fetcher import FetcherReachedHeadEvent
from bridge.transfer_recorder import TransferRecorder


class ConfirmationTaskPlanner:
    def __init__(
        self,
        sync_persistence_time: float,
        transfer_event_queue: Queue,
        home_bridge_event_queue: Queue,
        confirmation_task_queue: Queue,
    ) -> None:
        self.logger = logging.getLogger(
            "bridge.confirmation_task_planner.ConfirmationTaskPlanner"
        )

        self.recorder = TransferRecorder()
        self.sync_persistence_time = sync_persistence_time

        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_event_queue = home_bridge_event_queue

        self.confirmation_task_queue = confirmation_task_queue

    def run(self):
        self.logger.info("Starting")
        try:
            greenlets = [
                gevent.spawn(self.process_transfer_events),
                gevent.spawn(self.process_home_bridge_events),
            ]
            gevent.joinall(greenlets, raise_error=True)
        finally:
            self.logger.info("Stopping")
            for greenlet in greenlets:
                greenlet.kill()

    def process_transfer_events(self) -> None:
        while True:
            event = self.transfer_event_queue.get()
            if isinstance(event, FetcherReachedHeadEvent):
                self.logger.info("Transfer events are in sync now")
            else:
                self.logger.info("Received transfer to confirm")
                self.recorder.apply_proper_event(event)

    def process_home_bridge_events(self) -> None:
        while True:
            event = self.home_bridge_event_queue.get()
            if isinstance(event, FetcherReachedHeadEvent):
                self.logger.info("Home bridge is in sync now")
                # Let's check that this has not been for too long in the queue
                if time.time() - event.timestamp < self.sync_persistence_time:
                    self.check_for_confirmation_tasks()
            else:
                self.logger.info("Received home bridge event")
                self.recorder.apply_proper_event(event)

    def check_for_confirmation_tasks(self) -> None:
        confirmation_tasks = self.recorder.pull_transfers_to_confirm()
        self.logger.info(
            f"Scheduling {len(confirmation_tasks)} confirmation transactions"
        )
        for confirmation_task in confirmation_tasks:
            self.confirmation_task_queue.put(confirmation_task)
