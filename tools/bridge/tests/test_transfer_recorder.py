import logging
from itertools import count

import pytest
from eth_typing import Hash32
from eth_utils import int_to_big_endian
from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
    ZERO_ADDRESS,
)
from bridge.events import BalanceCheck, IsValidatorCheck
from bridge.transfer_recorder import TransferRecorder
from bridge.utils import compute_transfer_hash


@pytest.fixture
def hashes():
    """A generator that produces an infinite, non-repeatable sequence of hashes."""
    return (int_to_big_endian(12345).rjust(32, b"\x00") for counter in count())


@pytest.fixture
def hash_(hashes):
    """A single hash."""
    return next(hashes)


def make_transfer_event(
    transaction_hash: Hash32 = Hash32(int_to_big_endian(12345).rjust(32, b"\x00")),
    from_="0x345DeAd084E056dc78a0832E70B40C14B6323458",
    to="0x1ADb0A4853bf1D564BbAD7565b5D50b33D20af60",
    value=1,
) -> AttributeDict:
    return AttributeDict(
        {
            "event": TRANSFER_EVENT_NAME,
            "transactionHash": HexBytes(transaction_hash),
            "blockNumber": 1,
            "transactionIndex": 0,
            "logIndex": 0,
            "args": AttributeDict({"from": from_, "to": to, "value": value}),
        }
    )


def make_transfer_hash_event(
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
    return (make_transfer_event(transaction_hash) for transaction_hash in hashes)


@pytest.fixture
def transfer_event(transfer_events):
    """A single transfer event."""
    return next(transfer_events)


@pytest.fixture
def confirmation_events(hashes):
    """A generator that produces an infinite, non-repeatable sequence of confirmation events."""
    return (
        make_transfer_hash_event(
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
        make_transfer_hash_event(COMPLETION_EVENT_NAME, transfer_hash, transaction_hash)
        for transfer_hash, transaction_hash in zip(hashes, hashes)
    )


@pytest.fixture
def completion_event(completion_events):
    """A single completion event."""
    return next(completion_events)


@pytest.fixture
def minimum_balance():
    return 10 ** 18


@pytest.fixture
def recorder(minimum_balance):
    """A transfer recorder."""
    recorder = TransferRecorder(minimum_balance=minimum_balance)
    recorder.apply_event(BalanceCheck(minimum_balance))
    recorder.apply_event(IsValidatorCheck(True))
    return recorder


@pytest.fixture()
def fresh_recorder(minimum_balance):
    return TransferRecorder(minimum_balance=minimum_balance)


def test_log_current_state_fresh(fresh_recorder, caplog):
    caplog.set_level(logging.INFO)
    fresh_recorder.log_current_state()
    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert message.startswith("reporting internal state")
    assert "not validating" in message
    assert "balance -unknown-" in message


def test_log_current_state(recorder, caplog):
    caplog.set_level(logging.INFO)
    recorder.log_current_state()
    assert len(caplog.records) == 1
    message = caplog.records[0].message
    assert message.startswith("reporting internal state")
    assert "not validating" not in message
    assert "balance 1 coins" in message


def test_is_balance_sufficient(fresh_recorder):
    assert not fresh_recorder.is_balance_sufficient
    fresh_recorder.apply_event(BalanceCheck(balance=2 * 10 ** 18))
    assert fresh_recorder.is_balance_sufficient

    fresh_recorder.apply_event(BalanceCheck(balance=10 ** 15))
    assert not fresh_recorder.is_balance_sufficient


def test_is_validating(fresh_recorder):
    assert not fresh_recorder.is_validating
    fresh_recorder.apply_event(IsValidatorCheck(is_validator=True))
    assert not fresh_recorder.is_validating
    fresh_recorder.apply_event(BalanceCheck(balance=2 * 10 ** 18))
    assert fresh_recorder.is_validating


def test_skip_bad_transfer_zero_amount(recorder):
    recorder.apply_event(make_transfer_event(value=0))
    assert not recorder.transfer_events


def test_skip_bad_transfer_zero_address(recorder):
    recorder.apply_event(make_transfer_event(from_=ZERO_ADDRESS))
    assert not recorder.transfer_events


def test_recorder_pull_transfers(recorder):
    event = make_transfer_event()
    recorder.apply_event(event)
    assert recorder.transfer_events
    to_confirm = recorder.pull_transfers_to_confirm()
    assert to_confirm == [event]

    to_confirm = recorder.pull_transfers_to_confirm()
    assert to_confirm == []


def test_recorder_plans_transfers(recorder, transfer_event):
    recorder.apply_event(transfer_event)
    assert recorder.pull_transfers_to_confirm() == [transfer_event]


def test_recorder_does_not_plan_transfers_twice(recorder, transfer_event):
    recorder.apply_event(transfer_event)
    assert recorder.pull_transfers_to_confirm() == [transfer_event]
    assert len(recorder.pull_transfers_to_confirm()) == 0


def test_recorder_does_not_plan_confirmed_transfer(recorder, hashes):
    transfer_event = make_transfer_event(transaction_hash=next(hashes))

    confirmation_event = make_transfer_hash_event(
        CONFIRMATION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )
    recorder.apply_event(transfer_event)
    recorder.apply_event(confirmation_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0


def test_recorder_does_not_plan_completed_transfer(recorder, hashes):
    transfer_event = make_transfer_event(transaction_hash=next(hashes))
    completion_event = make_transfer_hash_event(
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


def test_recorder_not_validating_if_not_validator(recorder):
    assert recorder.is_validating
    recorder.apply_event(IsValidatorCheck(False))
    assert not recorder.is_validating
    recorder.apply_event(IsValidatorCheck(True))
    assert recorder.is_validating


def test_transfer_recorder_drops_completed_transfers(recorder, hashes):
    transfer_event = make_transfer_event(transaction_hash=next(hashes))
    completion_event = make_transfer_hash_event(
        COMPLETION_EVENT_NAME, compute_transfer_hash(transfer_event), next(hashes)
    )

    recorder.apply_event(transfer_event)
    recorder.apply_event(completion_event)
    assert len(recorder.pull_transfers_to_confirm()) == 0
