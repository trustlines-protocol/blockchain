#! pytest

from typing import Any, List

import attr
import eth_tester.exceptions
import pytest
from web3.datastructures import AttributeDict

from .data_generation import make_block_header


@pytest.fixture()
def deposit_contract_released_deposits(
    chain_cleanup, deposit_locker_contract_with_deposits, web3, chain, release_timestamp
):
    """returns a deposit contract from which the deposits can be withdrawn"""
    contract = deposit_locker_contract_with_deposits
    chain.time_travel(release_timestamp + 1)
    chain.mine_block()

    return contract


def test_init_already_initialized(
    deposit_locker_contract, accounts, deposit_locker_init
):
    """verifies that we cannot call the init function twice"""
    contract = deposit_locker_contract
    auction_contract_address = accounts[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        deposit_locker_init(contract, auction_contract_address)


def test_init_not_owner(
    non_initialized_deposit_locker_contract_session, accounts, release_timestamp
):
    contract = non_initialized_deposit_locker_contract_session
    validator_contract_address = accounts[0]
    auction_contract_address = accounts[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(
            _releaseTimestamp=release_timestamp,
            _slasher=validator_contract_address,
            _depositorsProxy=auction_contract_address,
        ).transact({"from": accounts[1]})


def test_init_release_time_in_the_past(
    non_initialized_deposit_locker_contract_session, accounts, web3
):
    contract = non_initialized_deposit_locker_contract_session
    validator_contract_address = accounts[0]
    auction_contract_address = accounts[1]
    now = web3.eth.getBlock("latest").timestamp

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(
            _releaseTimestamp=now,
            _slasher=validator_contract_address,
            _depositorsProxy=auction_contract_address,
        ).transact({"from": web3.eth.defaultAccount})


def test_owner_after_init(deposit_locker_contract):
    contract = deposit_locker_contract

    assert (
        contract.functions.owner().call()
        == "0x0000000000000000000000000000000000000000"
    )


def test_withdraw(deposit_contract_released_deposits, accounts, web3, deposit_amount):
    """test whether we can withdraw after block 10"""
    contract = deposit_contract_released_deposits

    pre_balance = web3.eth.getBalance(accounts[0])
    assert contract.functions.canWithdraw(accounts[0]).call()

    tx = contract.functions.withdraw().transact({"from": accounts[0]})
    gas_used = web3.eth.getTransactionReceipt(tx).gasUsed

    assert not contract.functions.canWithdraw(accounts[0]).call()
    new_balance = web3.eth.getBalance(accounts[0])

    assert new_balance - pre_balance == deposit_amount - gas_used


def test_withdraw_too_soon(
    deposit_locker_contract_with_deposits, accounts, deposit_amount
):
    """test whether we can withdraw before deposits are released"""
    contract = deposit_locker_contract_with_deposits

    assert contract.functions.canWithdraw(accounts[0]).call()

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.withdraw().transact({"from": accounts[0]})


def test_withdraw_not_initialized(
    non_initialized_deposit_locker_contract_session, accounts
):
    contract = non_initialized_deposit_locker_contract_session

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.withdraw().transact({"from": accounts[0]})


def test_slash_not_initialized(
    non_initialized_deposit_locker_contract_session, accounts
):
    contract = non_initialized_deposit_locker_contract_session

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.slash(accounts[0]).transact({"from": accounts[0]})


def test_register_depositor_not_initialized(
    non_initialized_deposit_locker_contract_session, accounts
):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        non_initialized_deposit_locker_contract_session.functions.registerDepositor(
            accounts[0]
        ).transact({"from": accounts[0]})


def test_deposit_not_initialized(
    non_initialized_deposit_locker_contract_session, accounts
):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        non_initialized_deposit_locker_contract_session.functions.deposit(0).transact(
            {"from": accounts[0], "value": 0}
        )


def test_event_withdraw(
    deposit_contract_released_deposits, deposit_amount, validators, web3
):
    contract = deposit_contract_released_deposits

    withdrawer = validators[0]

    latest_block_number = web3.eth.blockNumber

    contract.functions.withdraw().transact({"from": withdrawer})

    event = contract.events.Withdraw.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["withdrawer"] == withdrawer
    assert event["value"] == deposit_amount


def test_event_slash(
    deposit_locker_contract_with_deposits,
    validator_slasher_contract,
    malicious_validator_address,
    malicious_validator_key,
    deposit_amount,
    web3,
):

    latest_block_number = web3.eth.blockNumber

    timestamp = 100
    signed_block_header_one = make_block_header(
        timestamp=timestamp, private_key=malicious_validator_key
    )
    signed_block_header_two = make_block_header(
        timestamp=timestamp, private_key=malicious_validator_key
    )

    validator_slasher_contract.functions.reportMaliciousValidator(
        signed_block_header_one.unsignedBlockHeader,
        signed_block_header_one.signature,
        signed_block_header_two.unsignedBlockHeader,
        signed_block_header_two.signature,
    ).transact()

    event = deposit_locker_contract_with_deposits.events.Slash.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["slashedDepositor"] == malicious_validator_address
    assert event["slashedValue"] == deposit_amount


@attr.s(auto_attribs=True)
class Env:
    deposit_locker: Any
    slasher: Any
    proxy: Any
    depositors: List[Any]
    other_accounts: List[Any]

    def register_depositor(self, depositor):
        return self.deposit_locker.functions.registerDepositor(depositor).transact(
            {"from": self.proxy}
        )

    def register_all_depositors(self):
        for d in self.depositors:
            self.register_depositor(d)

    def deposit(self, value_per_depositor, total_value):
        return self.deposit_locker.functions.deposit(value_per_depositor).transact(
            {"from": self.proxy, "value": total_value}
        )

    def slash(self, depositor):
        return self.deposit_locker.functions.slash(depositor).transact(
            {"from": self.slasher}
        )

    def withdraw(self, depositor):
        return self.deposit_locker.functions.withdraw().transact({"from": depositor})

    def can_withdraw(self, depositor):
        return self.deposit_locker.functions.canWithdraw(depositor).call()


@pytest.fixture(scope="session")
def testenv(deploy_contract, accounts, web3, release_timestamp):
    """return an initialized Env instance"""
    deposit_locker = deploy_contract("DepositLocker")
    slasher = accounts[1]
    proxy = accounts[2]
    depositors = accounts[3:6]
    other_accounts = accounts[6:]
    deposit_locker.functions.init(
        _releaseTimestamp=release_timestamp, _slasher=slasher, _depositorsProxy=proxy
    ).transact({"from": web3.eth.defaultAccount})

    return Env(
        deposit_locker=deposit_locker,
        slasher=slasher,
        proxy=proxy,
        depositors=depositors,
        other_accounts=other_accounts,
    )


@pytest.fixture()
def value_per_depositor():
    return 1000


@pytest.fixture()
def testenv_deposited(testenv, value_per_depositor):
    """return a test environment, with all depositors registered and the deposit already made"""
    testenv.register_all_depositors()
    testenv.deposit(value_per_depositor, len(testenv.depositors) * value_per_depositor)
    return testenv


def test_register_from_non_proxy_throws(testenv, web3):
    """make sure we can only register a depositor from the proxy"""
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit_locker.functions.registerDepositor(
            testenv.depositors[0]
        ).transact({"from": web3.eth.defaultAccount})


def test_register_same_depositor_throws(testenv, web3):
    """make sure we can only register a depositor once"""

    print(testenv.depositors)
    testenv.register_depositor(testenv.depositors[0])
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.register_depositor(testenv.depositors[0])


def test_register_after_deposit_throws(testenv_deposited):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_deposited.register_depositor(testenv_deposited.other_accounts[0])


def test_deposit_with_no_depositors_throws(testenv):
    """a depositor must have been registers for deposit to work"""
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(100, 100)


def test_register_logs_event(testenv):
    assert (
        testenv.deposit_locker.events.DepositorRegistered.createFilter(
            fromBlock=0
        ).get_all_entries()
        == []
    )

    testenv.register_all_depositors()

    events = testenv.deposit_locker.events.DepositorRegistered.createFilter(
        fromBlock=0
    ).get_all_entries()
    assert len(events) == len(testenv.depositors)
    print(events[0].args)
    expected_args = [
        AttributeDict({"depositorAddress": depositor, "numberOfDepositors": i + 1})
        for i, depositor in enumerate(testenv.depositors)
    ]
    args = [ev.args for ev in events]
    assert args == expected_args


def test_deposit_with_right_amount_logs_event(testenv):
    testenv.register_all_depositors()
    testenv.deposit(3456, len(testenv.depositors) * 3456)
    events = testenv.deposit_locker.events.Deposit.createFilter(
        fromBlock=0
    ).get_all_entries()
    assert len(events) == 1
    assert events[0].args == AttributeDict(
        {
            "totalValue": 3456 * len(testenv.depositors),
            "valuePerDepositor": 3456,
            "numberOfDepositors": len(testenv.depositors),
        }
    )


def test_deposit_twice_throws(testenv):
    testenv.register_all_depositors()
    testenv.deposit(100, len(testenv.depositors) * 100)
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(100, len(testenv.depositors) * 100)


def test_deposit_unequal_amount(testenv):
    """total value send must match sum of deposits"""
    testenv.register_all_depositors()
    total_deposit = 100 * len(testenv.depositors)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(100, total_deposit + 1)


def test_deposit_overflow_throws(testenv):
    """total amount should not overflow"""
    testenv.register_all_depositors()
    # Create amount that will overflow
    per_depositor = (100 + 2 ** 256) // len(testenv.depositors)
    total_deposit = (per_depositor * len(testenv.depositors)) % 2 ** 256

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(per_depositor, total_deposit)


def test_zero_deposit_throws(testenv):
    """deposit must be positive"""
    testenv.register_all_depositors()
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(0, 0)


def test_slash_from_non_slasher_throws(testenv):
    testenv.register_all_depositors()
    testenv.deposit(100, len(testenv.depositors) * 100)
    depositor = testenv.depositors[0]

    assert testenv.can_withdraw(depositor)
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit_locker.functions.slash(depositor).transact(
            {"from": testenv.depositors[0]}
        )


def test_slash_after_deposit_can_not_withdraw(testenv_deposited):
    depositor = testenv_deposited.depositors[0]
    assert testenv_deposited.can_withdraw(depositor)
    testenv_deposited.slash(depositor)
    assert not testenv_deposited.can_withdraw(depositor)


def test_slash_after_deposit_burn_deposit(
    testenv_deposited, web3, value_per_depositor, block_reward_amount
):
    burn_address = "0x0000000000000000000000000000000000000000"
    contract_address = testenv_deposited.deposit_locker.address

    burn_address_balance_before = web3.eth.getBalance(burn_address)
    contract_address_balance_before = web3.eth.getBalance(contract_address)

    # The burning address is in this testing scenario also the address getting
    # the transaction fees and block rewards. To have a clear calculation make
    # sure the transaction has no fees.
    testenv_deposited.deposit_locker.functions.slash(
        testenv_deposited.depositors[0]
    ).transact({"from": testenv_deposited.slasher, "gasPrice": 0})

    burn_address_balance_after = web3.eth.getBalance(burn_address)
    contract_address_balance_after = web3.eth.getBalance(contract_address)

    assert (
        burn_address_balance_after
        == burn_address_balance_before + value_per_depositor + block_reward_amount
    )
    assert (
        contract_address_balance_after
        == contract_address_balance_before - value_per_depositor
    )


def test_slash_twice_throws(testenv_deposited):
    depositor = testenv_deposited.depositors[0]
    assert testenv_deposited.can_withdraw(depositor)
    testenv_deposited.slash(depositor)
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_deposited.slash(depositor)


def test_slash_non_depositor_throws(testenv_deposited):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_deposited.slash(testenv_deposited.other_accounts[0])
