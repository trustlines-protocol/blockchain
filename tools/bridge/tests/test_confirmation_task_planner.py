from itertools import count

import pytest
from eth_typing import Hash32
from eth_utils import encode_hex, int_to_big_endian
from web3.datastructures import AttributeDict

from bridge.confirmation_task_planner import TransferRecorder
from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
)


@pytest.fixture
def transfer_hashes():
    """A generator that produces an infinite, non-repeatable sequence of hashes."""
    return (int_to_big_endian(counter).rjust(32, b"\x00") for counter in count())


@pytest.fixture
def transfer_hash(transfer_hashes):
    """A single transfer hash."""
    return next(transfer_hashes)


def get_transfer_hash_event(event_name: str, transfer_hash: Hash32) -> AttributeDict:
    return AttributeDict(
        {
            "event": event_name,
            "args": AttributeDict({"transferHash": encode_hex(transfer_hash)}),
        }
    )


@pytest.fixture
def transfer_events(transfer_hashes):
    """A generator that produces an infinite, non-repeatable sequence of transfer events."""
    return (
        get_transfer_hash_event(TRANSFER_EVENT_NAME, transfer_hash)
        for transfer_hash in transfer_hashes
    )


@pytest.fixture
def transfer_event(transfer_events):
    """A single transfer event."""
    return next(transfer_events)


@pytest.fixture
def confirmation_events(transfer_hashes):
    """A generator that produces an infinite, non-repeatable sequence of confirmation events."""
    return (
        get_transfer_hash_event(CONFIRMATION_EVENT_NAME, transfer_hash)
        for transfer_hash in transfer_hashes
    )


@pytest.fixture
def confirmation_event(confirmation_events):
    """A single confirmation event."""
    return next(confirmation_events)


@pytest.fixture
def completion_events(transfer_hashes):
    """A generator that produces an infinite, non-repeatable sequence of completion events."""
    return (
        get_transfer_hash_event(COMPLETION_EVENT_NAME, transfer_hash)
        for transfer_hash in transfer_hashes
    )


@pytest.fixture
def completion_event(completion_events):
    """A single completion event."""
    return next(completion_events)


@pytest.fixture
def sync_persistence_time():
    """The time the transfer recorder assumes the sync status will persist."""
    return 2


@pytest.fixture
def recorder(sync_persistence_time):
    """A transfer recorder."""
    return TransferRecorder(sync_persistence_time)


def test_recorder_is_in_sync_if_home_chain_is_in_sync(recorder, sync_persistence_time):
    assert not recorder.is_in_sync(10)
    recorder.apply_home_chain_synced_event(10)
    assert recorder.is_in_sync(10)
    assert recorder.is_in_sync(10 + sync_persistence_time - 0.01)
    assert not recorder.is_in_sync(10 + sync_persistence_time + 0.01)


def test_sync_time_can_not_be_reduced(recorder):
    recorder.apply_home_chain_synced_event(2)
    recorder.apply_home_chain_synced_event(2)  # this is fine
    with pytest.raises(ValueError):
        recorder.apply_home_chain_synced_event(1)  # this is not


def test_recorder_plans_transfers_if_in_sync(recorder, transfer_event):
    recorder.apply_proper_event(transfer_event)
    recorder.apply_home_chain_synced_event(10)
    assert recorder.pull_transfers_to_confirm(10) == [transfer_event]


def test_recorder_does_not_plan_transfer_if_not_in_sync(recorder, transfer_event):
    recorder.apply_proper_event(transfer_event)
    assert len(recorder.pull_transfers_to_confirm(10)) == 0


def test_recorder_does_not_plan_transfers_twice(recorder, transfer_event):
    recorder.apply_proper_event(transfer_event)
    recorder.apply_home_chain_synced_event(10)
    assert recorder.pull_transfers_to_confirm(10) == [transfer_event]
    assert len(recorder.pull_transfers_to_confirm(10)) == 0


def test_recorder_does_not_plan_confirmed_transfer(recorder, transfer_hash):
    transfer_event = get_transfer_hash_event(TRANSFER_EVENT_NAME, transfer_hash)
    confirmation_event = get_transfer_hash_event(CONFIRMATION_EVENT_NAME, transfer_hash)
    recorder.apply_proper_event(transfer_event)
    recorder.apply_proper_event(confirmation_event)
    recorder.apply_home_chain_synced_event(10)
    assert len(recorder.pull_transfers_to_confirm(10)) == 0


def test_recorder_does_not_plan_completed_transfer(recorder, transfer_hash):
    transfer_event = get_transfer_hash_event(TRANSFER_EVENT_NAME, transfer_hash)
    completion_event = get_transfer_hash_event(COMPLETION_EVENT_NAME, transfer_hash)
    recorder.apply_proper_event(transfer_event)
    recorder.apply_proper_event(completion_event)
    recorder.apply_home_chain_synced_event(10)
    assert len(recorder.pull_transfers_to_confirm(10)) == 0
