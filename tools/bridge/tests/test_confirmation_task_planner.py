from itertools import count

import pytest
from eth_typing import Hash32
from eth_utils import int_to_big_endian
from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from bridge.confirmation_task_planner import TransferRecorder
from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
)
from bridge.utils import compute_transfer_hash


@pytest.fixture
def hashes():
    """A generator that produces an infinite, non-repeatable sequence of hashes."""
    return (int_to_big_endian(counter).rjust(32, b"\x00") for counter in count())


@pytest.fixture
def transfer_hash(hashes):
    """A single transfer hash."""
    return next(hashes)


def get_transfer_event(transaction_hash: Hash32) -> AttributeDict:
    return AttributeDict(
        {
            "event": TRANSFER_EVENT_NAME,
            "transactionHash": HexBytes(transaction_hash),
            "logIndex": 0,
        }
    )


def get_transfer_hash_event(
    event_name: str, transfer_hash: Hash32, transaction_hash: Hash32
) -> AttributeDict:
    return AttributeDict(
        {
            "event": event_name,
            "transactionHash": HexBytes(transaction_hash),
            "logIndex": 0,
            "args": AttributeDict({"transferHash": HexBytes(transfer_hash)}),
        }
    )


@pytest.fixture
def transfer_events(hashes):
    """A generator that produces an infinite, non-repeatable sequence of transfer events."""
    return (get_transfer_event(transaction_hash) for transaction_hash in hashes)


@pytest.fixture
def transfer_event(transfer_events):
    """A single transfer event."""
    return next(transfer_events)


@pytest.fixture
def confirmation_events(hashes):
    """A generator that produces an infinite, non-repeatable sequence of confirmation events."""
    return (
        get_transfer_hash_event(
            CONFIRMATION_EVENT_NAME, transfer_hash, transaction_hash
        )
        for transfer_hash, transaction_hash in zip(hashes, hashes)
    )


@pytest.fixture
def confirmation_event(confirmation_events):
    """A single confirmation event."""
    return next(confirmation_events)


@pytest.fixture
def completion_events(hashes):
    """A generator that produces an infinite, non-repeatable sequence of completion events."""
    return (
        get_transfer_hash_event(COMPLETION_EVENT_NAME, transfer_hash, transaction_hash)
        for transfer_hash, transaction_hash in zip(hashes, hashes)
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


def test_recorder_does_not_plan_confirmed_transfer(recorder, transfer_hash, hashes):
    transfer_event = get_transfer_hash_event(
        TRANSFER_EVENT_NAME, transfer_hash, next(hashes)
    )
    confirmation_event = get_transfer_hash_event(
        CONFIRMATION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )
    recorder.apply_proper_event(transfer_event)
    recorder.apply_proper_event(confirmation_event)
    recorder.apply_home_chain_synced_event(10)
    assert len(recorder.pull_transfers_to_confirm(10)) == 0


def test_recorder_does_not_plan_completed_transfer(recorder, transfer_hash, hashes):
    transfer_event = get_transfer_hash_event(
        TRANSFER_EVENT_NAME, transfer_hash, next(hashes)
    )
    completion_event = get_transfer_hash_event(
        COMPLETION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )
    recorder.apply_proper_event(transfer_event)
    recorder.apply_proper_event(completion_event)
    recorder.apply_home_chain_synced_event(10)
    assert len(recorder.pull_transfers_to_confirm(10)) == 0
