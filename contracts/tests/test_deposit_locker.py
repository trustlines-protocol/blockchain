#! pytest

import pytest
import eth_tester.exceptions
from .data_generation import make_block_header


@pytest.fixture()
def deposit_contract_on_longer_chain(
    chain_cleanup, deposit_locker_contract_with_deposits, web3, chain
):
    """gives a chain long enough to be able to withdraw the deposit of the deposit contract"""
    contract = deposit_locker_contract_with_deposits

    block_to_reach = contract.functions.releaseBlockNumber().call()
    current_block = web3.eth.blockNumber
    to_mine = block_to_reach - current_block

    chain.mine_blocks(to_mine)

    return contract


def test_init_already_initialized(deposit_locker_contract, accounts):
    """verifies that we cannot call the init function twice"""
    contract = deposit_locker_contract
    validator_contract_address = accounts[0]
    release_block_number = 100
    auction_contract_address = accounts[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(
            release_block_number, validator_contract_address, auction_contract_address
        ).transact({"from": accounts[0]})


def test_init_not_owner(non_initialised_deposit_locker_contract_session, accounts):
    contract = non_initialised_deposit_locker_contract_session
    validator_contract_address = accounts[0]
    release_block_number = 100
    auction_contract_address = accounts[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(
            release_block_number, validator_contract_address, auction_contract_address
        ).transact({"from": accounts[1]})


def test_init_passed_realease_block(
    non_initialised_deposit_locker_contract_session, accounts, web3
):
    contract = non_initialised_deposit_locker_contract_session
    validator_contract_address = accounts[0]
    release_block = web3.eth.blockNumber - 1

    auction_contract_address = accounts[1]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(
            release_block, validator_contract_address, auction_contract_address
        ).transact({"from": web3.eth.defaultAccount})


def test_owner_after_init(deposit_locker_contract):
    contract = deposit_locker_contract

    assert (
        contract.functions.owner().call()
        == "0x0000000000000000000000000000000000000000"
    )


def test_withdraw(deposit_contract_on_longer_chain, accounts, web3, deposit_amount):
    """test whether we can withdraw after block 10"""
    contract = deposit_contract_on_longer_chain

    pre_balance = web3.eth.getBalance(accounts[0])
    assert contract.functions.deposits(accounts[0]).call() == deposit_amount

    tx = contract.functions.withdraw().transact({"from": accounts[0]})
    gas_used = web3.eth.getTransactionReceipt(tx).gasUsed

    assert contract.functions.deposits(accounts[0]).call() == 0
    new_balance = web3.eth.getBalance(accounts[0])

    assert new_balance - pre_balance == deposit_amount - gas_used


def test_withdraw_too_soon(
    deposit_locker_contract_with_deposits, accounts, deposit_amount
):
    """test whether we can withdraw before releaseBlockNumber have been mined"""
    contract = deposit_locker_contract_with_deposits

    assert contract.functions.deposits(accounts[0]).call() == deposit_amount

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.withdraw().transact({"from": accounts[0]})


def test_withdraw_not_initialised(
    non_initialised_deposit_locker_contract_session, accounts
):
    contract = non_initialised_deposit_locker_contract_session

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.withdraw().transact({"from": accounts[0]})


def test_slash_not_initialised(
    non_initialised_deposit_locker_contract_session, accounts
):
    contract = non_initialised_deposit_locker_contract_session

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.slash(accounts[0]).transact({"from": accounts[0]})


def test_event_withdraw(
    deposit_contract_on_longer_chain, malicious_non_validator_address, web3
):
    contract = deposit_contract_on_longer_chain

    # Use the malicious_non_validator_address, since he has not deposit already.

    latest_block_number = web3.eth.blockNumber

    deposit = 10000000
    contract.functions.deposit(malicious_non_validator_address).transact(
        {"from": malicious_non_validator_address, "value": deposit}
    )

    contract.functions.withdraw().transact({"from": malicious_non_validator_address})

    event = contract.events.Withdraw.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["withdrawer"] == malicious_non_validator_address
    assert event["value"] == deposit


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

    assert event["validator"] == malicious_validator_address
    assert event["slashedValue"] == deposit_amount
