import logging
import time

from gevent.queue import Queue

from bridge.event_fetcher import FetcherReachedHeadEvent
from bridge.events import ChainRole
from bridge.service import Service, run_services
from bridge.transfer_recorder import TransferRecorder

logger = logging.getLogger(__name__)


class ConfirmationTaskPlanner:
    def __init__(
        self,
        recorder: TransferRecorder,
        sync_persistence_time: float,
        control_queue: Queue,
        transfer_event_queue: Queue,
        home_bridge_event_queue: Queue,
        confirmation_task_queue: Queue,
    ) -> None:
        self.recorder = recorder
        self.sync_persistence_time = sync_persistence_time

        self.control_queue = control_queue
        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_event_queue = home_bridge_event_queue

        self.confirmation_task_queue = confirmation_task_queue

        self.services = [
            Service(
                "process-transfer-events",
                self.process_events_from_queue,
                self.transfer_event_queue,
            ),
            Service(
                "process-home-bridge-events",
                self.process_events_from_queue,
                self.home_bridge_event_queue,
            ),
            Service(
                "process-control-events",
                self.process_events_from_queue,
                self.control_queue,
            ),
        ]

    def run(self):
        run_services(self.services)

    def process_events_from_queue(self, queue) -> None:
        while True:
            event = queue.get()
            self.recorder.apply_event(event)
            if (
                isinstance(event, FetcherReachedHeadEvent)
                and event.chain_role == ChainRole.home
            ):
                logger.debug(
                    "Home bridge is in sync now, last fetched reorg-safe block: %s",
                    event.last_fetched_block_number,
                )
                # Let's check that this has not been for too long in the queue
                if time.time() - event.timestamp < self.sync_persistence_time:
                    self.check_for_confirmation_tasks()

    def check_for_confirmation_tasks(self) -> None:
        confirmation_tasks = self.recorder.pull_transfers_to_confirm()
        logmsg = f"Scheduling {len(confirmation_tasks)} confirmation transactions"
        if len(confirmation_tasks) > 0:
            logger.info(logmsg)
        else:
            logger.debug(logmsg)

        for confirmation_task in confirmation_tasks:
            self.confirmation_task_queue.put(confirmation_task)
