import logging
import time

from gevent.queue import Queue

from bridge.event_fetcher import FetcherReachedHeadEvent
from bridge.service import Service, run_services
from bridge.transfer_recorder import TransferRecorder

logger = logging.getLogger(__name__)


class ConfirmationTaskPlanner:
    def __init__(
        self,
        sync_persistence_time: float,
        minimum_balance: int,
        control_queue: Queue,
        transfer_event_queue: Queue,
        home_bridge_event_queue: Queue,
        confirmation_task_queue: Queue,
    ) -> None:
        self.recorder = TransferRecorder(minimum_balance)
        self.sync_persistence_time = sync_persistence_time

        self.control_queue = control_queue
        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_event_queue = home_bridge_event_queue

        self.confirmation_task_queue = confirmation_task_queue

        self.services = [
            Service("process-transfer-events", self.process_transfer_events),
            Service("process-home-bridge-events", self.process_home_bridge_events),
            Service("process-control-events", self.process_control_events),
        ]

    def run(self):
        run_services(self.services)

    def process_transfer_events(self) -> None:
        while True:
            event = self.transfer_event_queue.get()
            if isinstance(event, FetcherReachedHeadEvent):
                logger.debug("Transfer events are in sync now")
            else:
                logger.debug("Received transfer to confirm")
                self.recorder.apply_proper_event(event)

    def process_home_bridge_events(self) -> None:
        while True:
            event = self.home_bridge_event_queue.get()
            if isinstance(event, FetcherReachedHeadEvent):
                logger.debug("Home bridge is in sync now")
                # Let's check that this has not been for too long in the queue
                if time.time() - event.timestamp < self.sync_persistence_time:
                    self.check_for_confirmation_tasks()
            else:
                logger.debug("Received home bridge event")
                self.recorder.apply_proper_event(event)

    def process_control_events(self) -> None:
        while True:
            event = self.control_queue.get()
            self.recorder.apply_control_event(event)

    def check_for_confirmation_tasks(self) -> None:
        confirmation_tasks = self.recorder.pull_transfers_to_confirm()
        logmsg = f"Scheduling {len(confirmation_tasks)} confirmation transactions"
        if len(confirmation_tasks) > 0:
            logger.info(logmsg)
        else:
            logger.debug(logmsg)

        for confirmation_task in confirmation_tasks:
            self.confirmation_task_queue.put(confirmation_task)
