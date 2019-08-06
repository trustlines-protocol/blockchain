from itertools import count

import pytest
from eth_utils import int_to_big_endian

from bridge.confirmation_task_planner import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
    ConfirmationTaskPlanner,
)


@pytest.fixture
def transfer_hashes():
    """A generator that produces an infinite, non-repeatable sequence of hashes."""
    return (int_to_big_endian(counter).rjust(32, b"\x00") for counter in count())


@pytest.fixture
def sync_persistence_time():
    """The time the confirmation task planner assumes the sync status will persist."""
    return 2


@pytest.fixture
def planner(sync_persistence_time):
    """A confirmation task planner."""
    return ConfirmationTaskPlanner(sync_persistence_time)


def test_planner_is_in_sync_if_home_chain_is_in_sync(planner, sync_persistence_time):
    assert not planner.is_in_sync(10)
    planner.apply_sync_completed(CONFIRMATION_EVENT_NAME, 10)
    assert not planner.is_in_sync(10)
    planner.apply_sync_completed(COMPLETION_EVENT_NAME, 10)
    assert planner.is_in_sync(10)


def test_planner_remains_in_sync_for_sync_persistence_time(
    planner, sync_persistence_time
):
    planner.apply_sync_completed(CONFIRMATION_EVENT_NAME, 10)
    planner.apply_sync_completed(
        COMPLETION_EVENT_NAME, 10 + sync_persistence_time * 0.5
    )
    assert planner.is_in_sync(10 + sync_persistence_time * 0.5 + 0.01)
    assert planner.is_in_sync(10 + sync_persistence_time - 0.01)
    assert not planner.is_in_sync(10 + sync_persistence_time + 0.01)


def test_sync_time_can_not_be_reduced(planner, transfer_hashes):
    for event_name in [CONFIRMATION_EVENT_NAME, COMPLETION_EVENT_NAME]:
        planner.apply_sync_completed(event_name, 2)
        planner.apply_sync_completed(event_name, 2)  # this is fine
        with pytest.raises(ValueError):
            planner.apply_sync_completed(event_name, 1)  # this is not


def test_planner_plans_transfers_if_in_sync(planner, transfer_hashes):
    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash(TRANSFER_EVENT_NAME, transfer_hash)
    planner.apply_sync_completed(CONFIRMATION_EVENT_NAME, 10)
    planner.apply_sync_completed(COMPLETION_EVENT_NAME, 10)
    assert planner.get_next_transfer_hashes(10) == {transfer_hash}


def test_planner_does_not_plan_transfer_if_not_in_sync(planner, transfer_hashes):
    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash(TRANSFER_EVENT_NAME, transfer_hash)
    assert len(planner.get_next_transfer_hashes(10)) == 0


def test_planner_does_not_plan_transfers_twice(planner, transfer_hashes):
    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash(TRANSFER_EVENT_NAME, transfer_hash)
    planner.apply_sync_completed(CONFIRMATION_EVENT_NAME, 10)
    planner.apply_sync_completed(COMPLETION_EVENT_NAME, 10)
    assert planner.get_next_transfer_hashes(10) == {transfer_hash}
    assert len(planner.get_next_transfer_hashes(10)) == 0
