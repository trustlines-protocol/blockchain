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
from bridge.events import BalanceCheck, IsValidatorCheck
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
def minimum_balance():
    return 1


@pytest.fixture
def recorder(minimum_balance):
    """A transfer recorder."""
    recorder = TransferRecorder(minimum_balance=minimum_balance)
    recorder.apply_event(BalanceCheck(minimum_balance))
    recorder.apply_event(IsValidatorCheck(True))
    return recorder


def test_recorder_plans_transfers(recorder, transfer_event):
    recorder.apply_event(transfer_event)
    assert recorder.pull_transfers_to_confirm() == [transfer_event]


def test_recorder_does_not_plan_transfers_twice(recorder, transfer_event):
    recorder.apply_event(transfer_event)
    assert recorder.pull_transfers_to_confirm() == [transfer_event]
    assert len(recorder.pull_transfers_to_confirm()) == 0


def test_recorder_does_not_plan_confirmed_transfer(recorder, transfer_hash, hashes):
    transfer_event = get_transfer_hash_event(
        TRANSFER_EVENT_NAME, transfer_hash, next(hashes)
    )
    confirmation_event = get_transfer_hash_event(
        CONFIRMATION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )
    recorder.apply_event(transfer_event)
    recorder.apply_event(confirmation_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0


def test_recorder_does_not_plan_completed_transfer(recorder, transfer_hash, hashes):
    transfer_event = get_transfer_hash_event(
        TRANSFER_EVENT_NAME, transfer_hash, next(hashes)
    )
    completion_event = get_transfer_hash_event(
        COMPLETION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )
    recorder.apply_event(transfer_event)
    recorder.apply_event(completion_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0


def test_recorder_does_not_plan_transfers_if_not_validating(
    recorder, minimum_balance, transfer_event
):
    recorder.apply_event(BalanceCheck(minimum_balance - 1))
    assert not recorder.is_validating

    recorder.apply_event(transfer_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0

    recorder.apply_event(BalanceCheck(minimum_balance))
    assert recorder.is_validating
    assert recorder.pull_transfers_to_confirm() == [transfer_event]


def test_recorder_not_validating_if_balance_below_minimum(recorder, minimum_balance):
    assert recorder.is_validating
    recorder.apply_event(BalanceCheck(minimum_balance - 1))
    assert not recorder.is_validating
    recorder.apply_event(BalanceCheck(minimum_balance))
    assert recorder.is_validating


def test_recorder_not_validating_if_not_validator(recorder, minimum_balance):
    assert recorder.is_validating
    recorder.apply_event(IsValidatorCheck(False))
    assert not recorder.is_validating
    recorder.apply_event(IsValidatorCheck(True))
    assert recorder.is_validating


def test_transfer_recorder_drops_completed_transfers(recorder, hashes):
    transfer_hash = next(hashes)
    transfer_event = get_transfer_hash_event(
        TRANSFER_EVENT_NAME, transfer_hash, next(hashes)
    )
    completion_event = get_transfer_hash_event(
        COMPLETION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )

    recorder.apply_event(transfer_event)
    recorder.apply_event(completion_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0
