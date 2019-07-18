import pytest

from eth_tester.exceptions import TransactionFailed


@pytest.fixture
def confirm(home_bridge_contract):
    """call confirmTransfer on the home_bridge_contract with less boilerplate"""

    class Confirm:
        transfer_hash = "0x" + b"     transfer-hash              ".hex()
        tx_hash = "0x" + b"     tx-hash                    ".hex()
        amount = 20000
        recipient = "0xFCB047cCD297048b6F31fbb2fef14001FefFa0f3"

        def __call__(self):
            return home_bridge_contract.functions.confirmTransfer(
                transferHash=self.transfer_hash,
                transactionHash=self.tx_hash,
                amount=self.amount,
                recipient=self.recipient,
            )

        def assert_event_matches(self, event):
            print("checking event", event)
            assert event.args.transferHash.hex() == self.transfer_hash[2:]
            assert event.args.transactionHash.hex() == self.tx_hash[2:]
            assert event.args.amount == self.amount
            assert event.args.recipient == self.recipient

    return Confirm()


def test_confirm_transfer_zero_address_recipient_throws(home_bridge_contract, confirm):
    confirm.recipient = "0x0000000000000000000000000000000000000000"
    with pytest.raises(TransactionFailed):
        confirm().transact()


def test_confirm_transfer_zero_amount_throws(home_bridge_contract, confirm):
    confirm.amount = 0
    with pytest.raises(TransactionFailed):
        confirm().transact()


def test_double_confirm_transfer(home_bridge_contract, confirm):
    confirm().transact()

    with pytest.raises(TransactionFailed):
        confirm().transact()


def test_confirm_transfer_emits_event(home_bridge_contract, web3, accounts, confirm):

    latest_block_number = web3.eth.blockNumber

    confirm().transact()

    events = home_bridge_contract.events.Confirmation.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()

    print("events:", events)
    assert len(events) == 1

    confirm.assert_event_matches(events[0])
    assert events[0].args.validator == accounts[0]


def test_confirm_throws_for_non_validator(home_bridge_contract, accounts, confirm):
    with pytest.raises(TransactionFailed):
        confirm().transact({"from": accounts[6]})


def test_complete_transfer(home_bridge_contract, proxy_validators, confirm, web3):
    """send confirmations from all validators.

This walks through a complete Transfer on the home bridge, with
additional confirmations from validators that are late.
"""
    required_confirmations = 2

    get_confirmation_events = home_bridge_contract.events.Confirmation.createFilter(
        fromBlock=web3.eth.blockNumber
    ).get_all_entries
    get_transfer_completed_events = home_bridge_contract.events.TransferCompleted.createFilter(
        fromBlock=web3.eth.blockNumber
    ).get_all_entries

    bridge_balance_before = web3.eth.getBalance(home_bridge_contract.address)
    assert (
        bridge_balance_before >= confirm.amount
    )  # We need at least that much for the test

    for validator in proxy_validators[:required_confirmations]:
        assert not get_transfer_completed_events()
        assert web3.eth.getBalance(confirm.recipient) == 0
        print(validator, "confirms")
        confirm().transact({"from": validator})

    transfer_completed_events = get_transfer_completed_events()
    print("transfer_completed_events", transfer_completed_events)
    assert len(transfer_completed_events) == 1
    confirm.assert_event_matches(transfer_completed_events[0])

    assert web3.eth.getBalance(confirm.recipient) == confirm.amount
    assert (
        web3.eth.getBalance(home_bridge_contract.address)
        == bridge_balance_before - confirm.amount
    )

    confirmation_events = get_confirmation_events()
    assert len(confirmation_events) == required_confirmations
    for event, validator in zip(confirmation_events, proxy_validators):
        confirm.assert_event_matches(event)
        assert event.args.validator == validator

    # make sure additional confirmations don't get through
    for validator in proxy_validators[required_confirmations:]:
        with pytest.raises(TransactionFailed):
            print(validator, "tries to confirm")
            confirm().transact({"from": validator})
