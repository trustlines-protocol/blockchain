#! pytest
from typing import Any, List, Optional

import attr
import eth_tester.exceptions
import pytest
from web3.datastructures import AttributeDict


def get_balance_function(web3=None, token_contract=None):
    if token_contract is None:
        return web3.eth.getBalance
    else:
        return lambda address: token_contract.functions.balanceOf(address).call()


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


@attr.s(auto_attribs=True)
class Env:
    deposit_locker: Any
    slasher: Any
    proxy: Any
    depositors: List[Any]
    other_accounts: List[Any]
    token_contract: Optional[Any]

    @property
    def use_token(self):
        return self.token_contract is not None

    def register_depositor(self, depositor):
        return self.deposit_locker.functions.registerDepositor(depositor).transact(
            {"from": self.proxy}
        )

    def register_all_depositors(self):
        for d in self.depositors:
            self.register_depositor(d)

    def deposit(self, value_per_depositor, total_value):
        return self.deposit_locker.functions.deposit(value_per_depositor).transact(
            # do not send eth along if token is used
            {"from": self.proxy, "value": total_value if not self.use_token else 0}
        )

    def slash(self, depositor):
        return self.deposit_locker.functions.slash(depositor).transact(
            {"from": self.slasher}
        )

    def withdraw(self, depositor):
        return self.deposit_locker.functions.withdraw().transact({"from": depositor})

    def can_withdraw(self, depositor):
        return self.deposit_locker.functions.canWithdraw(depositor).call()

    def balance_of(self, address):
        return get_balance_function(self.deposit_locker.web3, self.token_contract)(
            address
        )


@pytest.fixture(scope="session", params=["ETHDepositLocker", "TokenDepositLocker"])
def testenv(
    request,
    deploy_contract,
    accounts,
    web3,
    release_timestamp,
    premint_token_address,
    premint_token_value,
):
    """return an initialized Env instance"""
    token_contract = None
    if request.param == "TokenDepositLocker":
        token_name = "Trustlines Network Token"
        token_symbol = "TLN"
        token_decimal = 18
        token_constructor_args = (
            token_name,
            token_symbol,
            token_decimal,
            premint_token_address,
            premint_token_value,
        )

        token_contract = deploy_contract(
            "TrustlinesNetworkToken", constructor_args=token_constructor_args
        )

    deposit_locker = deploy_contract(request.param)
    slasher = accounts[1]
    proxy = accounts[2]
    depositors = accounts[3:6]
    other_accounts = accounts[6:]
    deposit_locker_init_args = {
        "_releaseTimestamp": release_timestamp,
        "_slasher": slasher,
        "_depositorsProxy": proxy,
    }
    if token_contract is not None:
        deposit_locker_init_args["_token"] = token_contract.address
    deposit_locker.functions.init(**deposit_locker_init_args).transact(
        {"from": web3.eth.defaultAccount}
    )

    testenv = Env(
        deposit_locker=deposit_locker,
        slasher=slasher,
        proxy=proxy,
        depositors=depositors,
        other_accounts=other_accounts,
        token_contract=token_contract,
    )

    if testenv.use_token:
        testenv.token_contract.functions.transfer(testenv.proxy, 100000).transact(
            {"from": premint_token_address}
        )
        testenv.token_contract.functions.approve(
            testenv.deposit_locker.address, 2 ** 256 - 1
        ).transact({"from": testenv.proxy})

    return testenv


@pytest.fixture()
def value_per_depositor():
    return 1000


@pytest.fixture()
def testenv_deposited(testenv, value_per_depositor, premint_token_address):
    """return a test environment, with all depositors registered and the deposit already made"""
    testenv.register_all_depositors()
    testenv.deposit(value_per_depositor, len(testenv.depositors) * value_per_depositor)
    return testenv


@pytest.fixture()
def testenv_deposits_released(testenv_deposited, release_timestamp, chain):
    chain.time_travel(release_timestamp + 1)
    chain.mine_block()

    return testenv_deposited


def test_withdraw(testenv_deposits_released, accounts, web3, value_per_depositor):
    """test whether we can withdraw after block 10"""
    withdrawer = accounts[3]
    testenv = testenv_deposits_released
    pre_balance = testenv.balance_of(withdrawer)
    assert testenv.can_withdraw(withdrawer)

    tx = testenv.withdraw(withdrawer)
    gas_used = web3.eth.getTransactionReceipt(tx).gasUsed

    assert not testenv.can_withdraw(withdrawer)
    new_balance = testenv.balance_of(withdrawer)

    if testenv.use_token:
        assert new_balance - pre_balance == value_per_depositor
    else:
        assert new_balance - pre_balance == value_per_depositor - gas_used


def test_withdraw_too_soon(testenv_deposited, accounts):
    """test whether we can withdraw before deposits are released"""
    testenv = testenv_deposited
    withdrawer = accounts[3]
    assert testenv.can_withdraw(withdrawer)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.withdraw(withdrawer)


def test_event_withdraw(testenv_deposits_released, value_per_depositor, accounts, web3):
    testenv = testenv_deposits_released
    withdrawer = accounts[3]

    latest_block_number = web3.eth.blockNumber

    testenv.withdraw(withdrawer)

    event = testenv.deposit_locker.events.Withdraw.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["withdrawer"] == withdrawer
    assert event["value"] == value_per_depositor


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


def test_deposit_right_amount(testenv, web3):
    testenv.register_all_depositors()

    contract_address = testenv.deposit_locker.address

    contract_address_balance_before = testenv.balance_of(contract_address)
    testenv.deposit(3456, len(testenv.depositors) * 3456)
    contract_address_balance_after = testenv.balance_of(contract_address)

    assert (
        contract_address_balance_after - contract_address_balance_before
        == len(testenv.depositors) * 3456
    )


def test_deposit_twice_throws(testenv):
    testenv.register_all_depositors()
    testenv.deposit(100, len(testenv.depositors) * 100)
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.deposit(100, len(testenv.depositors) * 100)


def test_deposit_unequal_amount(testenv):
    """total value send must match sum of deposits for ETH locker"""
    testenv.register_all_depositors()
    total_deposit = 100 * len(testenv.depositors)
    if not testenv.use_token:
        with pytest.raises(eth_tester.exceptions.TransactionFailed):
            testenv.deposit(100, total_deposit + 1)
    else:
        testenv.deposit(100, 0)


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


def test_slash_after_deposit_burn_deposit(testenv_deposited, web3, value_per_depositor):
    contract_address = testenv_deposited.deposit_locker.address
    contract_address_balance_before = testenv_deposited.balance_of(contract_address)

    testenv_deposited.deposit_locker.functions.slash(
        testenv_deposited.depositors[0]
    ).transact({"from": testenv_deposited.slasher})

    contract_address_balance_after = testenv_deposited.balance_of(contract_address)

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


def test_event_slash(testenv_deposited, value_per_depositor, web3):
    testenv = testenv_deposited
    latest_block_number = web3.eth.blockNumber

    depositor = testenv.depositors[0]
    testenv.slash(depositor)

    event = testenv.deposit_locker.events.Slash.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["slashedDepositor"] == depositor
    assert event["slashedValue"] == value_per_depositor
