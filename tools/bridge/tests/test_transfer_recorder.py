import logging

import pytest
from hexbytes import HexBytes
from web3.datastructures import AttributeDict

from bridge.constants import ZERO_ADDRESS
from bridge.events import BalanceCheck, IsValidatorCheck
from bridge.transfer_recorder import TransferRecorder


def make_event(
    *,
    _from="0x449458F2B2c67159A6E05166d4f80a5AC783182C",
    _to="0xb4c79daB8f259C7Aee6E5b2Aa729821864227e84",
    value=1200
):
    return AttributeDict(
        {
            "args": AttributeDict({"from": _from, "to": _to, "value": value}),
            "event": "Transfer",
            "logIndex": 0,
            "transactionIndex": 0,
            "transactionHash": HexBytes(
                "0xc7452af2de5730003e4b0e0d6481338013c65299e91637c4db65923a41118339"
            ),
            "address": "0x731a10897d267e19B34503aD902d0A29173Ba4B1",
            "blockHash": HexBytes(
                "0xa16a2b925878cba9a5179e415ca3a76c44a15a103516c6263c7a151a134061f5"
            ),
            "blockNumber": 5574,
        }
    )


@pytest.fixture()
def transfer_event():
    return AttributeDict(
        {
            "args": AttributeDict(
                {
                    "from": "0x449458F2B2c67159A6E05166d4f80a5AC783182C",
                    "to": "0xb4c79daB8f259C7Aee6E5b2Aa729821864227e84",
                    "value": 1200,
                }
            ),
            "event": "Transfer",
            "logIndex": 0,
            "transactionIndex": 0,
            "transactionHash": HexBytes(
                "0xc7452af2de5730003e4b0e0d6481338013c65299e91637c4db65923a41118339"
            ),
            "address": "0x731a10897d267e19B34503aD902d0A29173Ba4B1",
            "blockHash": HexBytes(
                "0xa16a2b925878cba9a5179e415ca3a76c44a15a103516c6263c7a151a134061f5"
            ),
            "blockNumber": 5574,
        }
    )


@pytest.fixture()
def fresh_recorder():
    return TransferRecorder(minimum_balance=10 ** 18)


@pytest.fixture()
def recorder():
    recorder = TransferRecorder(minimum_balance=10 ** 18)
    recorder.apply_event(BalanceCheck(balance=200 * 10 ** 18))
    recorder.apply_event(IsValidatorCheck(is_validator=True))
    return recorder


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
    assert "balance 2" in message


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


def test_skip_bad_transfer_zero_amount(recorder, transfer_event):
    recorder.apply_event(make_event(value=0))
    assert not recorder.transfer_events


def test_skip_bad_transfer_zero_address(recorder, transfer_event):
    recorder.apply_event(make_event(_from=ZERO_ADDRESS))
    assert not recorder.transfer_events


def test_recorder_pull_transfers(recorder):
    event = make_event()
    recorder.apply_event(event)
    assert recorder.transfer_events
    to_confirm = recorder.pull_transfers_to_confirm()
    assert to_confirm == [event]

    to_confirm = recorder.pull_transfers_to_confirm()
    assert to_confirm == []
