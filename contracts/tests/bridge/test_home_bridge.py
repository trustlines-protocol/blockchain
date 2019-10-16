import pytest
from eth_tester.exceptions import TransactionFailed


@pytest.fixture
def non_payable_recipient(deploy_contract):
    """non-payable contract"""
    return deploy_contract("TestNonPayableRecipient", constructor_args=())


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

        def reconfirm_completes_transfer(self):
            return home_bridge_contract.functions.reconfirmCompletesTransfer(
                transferHash=self.transfer_hash,
                transactionHash=self.tx_hash,
                amount=self.amount,
                recipient=self.recipient,
            ).call()

    return Confirm()


def test_confirm_transfer_zero_address_recipient_throws(home_bridge_contract, confirm):
    confirm.recipient = "0x0000000000000000000000000000000000000000"
    with pytest.raises(TransactionFailed):
        confirm().transact()


def test_confirm_transfer_zero_amount_throws(home_bridge_contract, confirm):
    confirm.amount = 0
    with pytest.raises(TransactionFailed):
        confirm().transact()


def test_multi_confirm_transfer(home_bridge_contract, confirm, web3):
    latest_block_number = web3.eth.blockNumber

    get_confirmation_events = home_bridge_contract.events.Confirmation.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries
    get_transfer_completed_events = home_bridge_contract.events.TransferCompleted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries

    def confirm_and_check():
        confirm().transact()
        assert len(get_confirmation_events()) == 1
        assert len(get_transfer_completed_events()) == 0

    for _ in range(10):
        confirm_and_check()


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
    required_confirmations = 3

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
        assert not confirm.reconfirm_completes_transfer()
        confirm().transact({"from": validator})

    transfer_completed_events = get_transfer_completed_events()
    print("transfer_completed_events", transfer_completed_events)
    assert len(transfer_completed_events) == 1
    confirm.assert_event_matches(transfer_completed_events[0])

    assert transfer_completed_events[0].args.coinTransferSuccessful

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


def test_complete_transfer_send_fails(
    home_bridge_contract, proxy_validators, confirm, web3, non_payable_recipient
):
    """send confirmations from all validators, recipient refuses to take coins

This walks through a complete Transfer on the home bridge, with
additional confirmations from validators that are late.
"""
    required_confirmations = 3
    confirm.recipient = non_payable_recipient.address

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

    assert not transfer_completed_events[0].args.coinTransferSuccessful

    assert web3.eth.getBalance(confirm.recipient) == 0
    assert web3.eth.getBalance(home_bridge_contract.address) == bridge_balance_before


def test_complete_transfer_validator_set_change(
    home_bridge_contract,
    proxy_validators,
    validator_proxy_with_validators,
    confirm,
    web3,
    system_address,
):
    """send some confirmations, change the validator set and make sure
    the contract handles that
"""
    required_confirmations = 3

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

    for validator in proxy_validators[: required_confirmations - 1]:
        assert not get_transfer_completed_events()
        assert web3.eth.getBalance(confirm.recipient) == 0
        print(validator, "confirms")
        confirm().transact({"from": validator})

    # replace the first validator
    validator_proxy_with_validators.functions.updateValidators(
        ["0x5413d1d9CaF79Bf01Cf821898D9B54ada014FbFA"] + proxy_validators[1:]
    ).transact({"from": system_address})

    for validator in proxy_validators[
        required_confirmations - 1 : required_confirmations + 1
    ]:
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
    assert len(confirmation_events) == required_confirmations + 1


def test_recheck_after_validator_set_change(
    home_bridge_contract,
    proxy_validators,
    validator_proxy_with_validators,
    confirm,
    web3,
    system_address,
):
    """send some confirmations, change the validator set in a way that
    the transfer has enough confirmations and let a validator, that
    already confirmed, recheck the transfer.
"""
    required_confirmations = 3

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

    for validator in proxy_validators[: required_confirmations - 1]:
        assert not get_transfer_completed_events()
        assert web3.eth.getBalance(confirm.recipient) == 0
        print(validator, "confirms")
        confirm().transact({"from": validator})
        assert not confirm.reconfirm_completes_transfer()

    new_proxy_validators = proxy_validators[: required_confirmations - 1] + [
        "0x5413d1d9CaF79Bf01Cf821898D9B54ada014FbFA"
    ]
    validator_proxy_with_validators.functions.updateValidators(
        new_proxy_validators
    ).transact({"from": system_address})

    assert confirm.reconfirm_completes_transfer()

    assert not get_transfer_completed_events()
    assert web3.eth.getBalance(confirm.recipient) == 0
    validator = new_proxy_validators[0]
    print(validator, "re-checks/confirms")
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
    assert len(confirmation_events) == required_confirmations - 1

    with pytest.raises(TransactionFailed):
        confirm.reconfirm_completes_transfer()
