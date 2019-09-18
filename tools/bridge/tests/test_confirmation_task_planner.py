import time

import gevent
import pytest
from gevent.queue import Queue

from bridge.confirmation_task_planner import ConfirmationTaskPlanner
from bridge.events import ChainRole, Event, FetcherReachedHeadEvent


def assert_events_in_queue(queue, events):
    """Asserts that all events are in the queue in the same order.
    This does not block, because it will examine the current items in the queue"""
    # Queue.queue gives the underlying collections.deque
    assert list(queue.queue) == list(events)


class TransferRecorderMock:
    def __init__(self):
        self.events = []
        self.transfers_to_confirm = []

    def apply_event(self, event):
        self.events.append(event)

    def pull_transfers_to_confirm(self):
        return self.transfers_to_confirm


@pytest.fixture()
def control_queue():
    return Queue()


@pytest.fixture()
def transfer_event_queue():
    return Queue()


@pytest.fixture()
def home_bridge_event_queue():
    return Queue()


@pytest.fixture()
def confirmation_task_queue():
    return Queue()


@pytest.fixture()
def transfer_recorder_mock():
    return TransferRecorderMock()


@pytest.fixture()
def confirmation_task_planner(
    control_queue,
    transfer_event_queue,
    home_bridge_event_queue,
    confirmation_task_queue,
    transfer_recorder_mock,
    spawn,
):
    confirmation_task_planner = ConfirmationTaskPlanner(
        transfer_recorder_mock,
        10,
        control_queue,
        transfer_event_queue,
        home_bridge_event_queue,
        confirmation_task_queue,
    )
    spawn(confirmation_task_planner.run)

    return confirmation_task_planner


def test_process_events_from_queue(
    confirmation_task_planner, transfer_recorder_mock, transfer_event_queue
):
    events = [Event(), Event(), Event()]
    for event in events:
        transfer_event_queue.put(event)

    # give control to confirmation planner
    gevent.sleep(0.001)
    assert transfer_recorder_mock.events == events


def test_check_for_confirmation_tasks(
    confirmation_task_planner, transfer_recorder_mock, confirmation_task_queue
):
    confirmation_task_planner.check_for_confirmation_tasks()
    assert len(confirmation_task_queue) == 0

    events = [Event(), Event(), Event()]
    transfer_recorder_mock.transfers_to_confirm = events
    confirmation_task_planner.check_for_confirmation_tasks()

    assert_events_in_queue(confirmation_task_queue, events)


def test_wait_for_fetcher_reached_head_event(
    confirmation_task_planner,
    transfer_recorder_mock,
    transfer_event_queue,
    control_queue,
    confirmation_task_queue,
):
    events = [Event(), Event(), Event()]
    for event in events:
        transfer_event_queue.put(event)
    transfer_recorder_mock.transfers_to_confirm = events

    # give control to confirmation planner
    gevent.sleep()
    assert len(confirmation_task_queue) == 0

    control_queue.put(FetcherReachedHeadEvent(time.time(), ChainRole.home, 0))
    # give control to confirmation planner
    gevent.sleep()
    assert_events_in_queue(confirmation_task_queue, events)


def test_too_old_fetcher_reached_head_event(
    confirmation_task_planner,
    transfer_recorder_mock,
    control_queue,
    confirmation_task_queue,
):
    events = [Event(), Event(), Event()]
    transfer_recorder_mock.transfers_to_confirm = events

    # give control to confirmation planner
    gevent.sleep()
    assert len(confirmation_task_queue) == 0

    control_queue.put(FetcherReachedHeadEvent(time.time() - 100, ChainRole.home, 0))
    # give control to confirmation planner
    gevent.sleep()
    assert len(confirmation_task_queue) == 0


def test_wrong_chain_fetcher_reached_head_event(
    confirmation_task_planner,
    transfer_recorder_mock,
    control_queue,
    confirmation_task_queue,
):
    events = [Event(), Event(), Event()]
    transfer_recorder_mock.transfers_to_confirm = events

    # give control to confirmation planner
    gevent.sleep()
    assert len(confirmation_task_queue) == 0

    control_queue.put(FetcherReachedHeadEvent(time.time(), ChainRole.foreign, 0))
    # give control to confirmation planner
    gevent.sleep()
    assert len(confirmation_task_queue) == 0
