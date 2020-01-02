#! pytest

import eth_tester.exceptions
import pytest
from tests.data_generation import make_block_header
from web3.exceptions import MismatchedABI


def test_get_validator(validator_set_contract_session, validators):

    assert validator_set_contract_session.functions.getValidators().call() == validators


def test_init_already_initialized(validator_set_contract_session, accounts):
    """verifies that we cannot call the init function twice"""

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.init(
            [accounts[0]], accounts[0]
        ).transact({"from": accounts[0]})


def test_remove_validator1(validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[1]).transact(
        {"from": accounts[0]}
    )
    assert contract.functions.pendingValidators(0).call() == validators[0]
    assert contract.functions.pendingValidators(1).call() == validators[2]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.pendingValidators(2).call()


def test_remove_validator0(validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact(
        {"from": accounts[0]}
    )
    # Mind that deleting an entry from the array replace the index to remove
    # with the last entry of the array and cut of the last index afterwards.
    assert contract.functions.pendingValidators(0).call() == validators[2]
    assert contract.functions.pendingValidators(1).call() == validators[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.pendingValidators(2).call()


def test_remove_validator_not_finalized(
    validator_set_contract_session, validators, accounts
):
    """verifies that we cannot remove a validator when the set of validator is not finalized"""
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[1]).transact(
        {"from": accounts[0]}
    )
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testRemoveValidator(validators[0]).transact(
            {"from": accounts[0]}
        )


def test_removing_validator_emits_initiate_change_event(
    validator_set_contract_session, validators, accounts
):

    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact(
        {"from": accounts[0]}
    )

    assert (
        len(contract.events.InitiateChange.createFilter(fromBlock=0).get_all_entries())
        == 1
    )


def test_initiate_change_event_parent_hash(
    web3, validator_set_contract_session, validators, accounts
):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact(
        {"from": accounts[0]}
    )

    latest_block_number = web3.eth.getBlock("latest")["number"]
    parent_hash_of_latest_block = web3.eth.getBlock(latest_block_number - 1)["hash"]
    parent_hash_of_event = contract.events.InitiateChange.createFilter(
        fromBlock=0
    ).get_all_entries()[0]["args"]["_parentHash"]

    assert parent_hash_of_event == parent_hash_of_latest_block


def test_initiate_change_event_new_set(
    validator_set_contract_session, validators, accounts
):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact(
        {"from": accounts[0]}
    )

    pending_validator_in_contract = contract.functions.pendingValidators(0).call()

    new_set = contract.events.InitiateChange.createFilter(
        fromBlock=0
    ).get_all_entries()[0]["args"]["_newSet"][0]

    assert new_set == pending_validator_in_contract


def test_get_validator_function_signature(validator_set_contract_session):
    contract = validator_set_contract_session

    signature = "getValidators()"

    try:
        contract.get_function_by_signature(signature)
    except ValueError:
        pytest.fail("no function with expected signature: " + signature)


def test_finalize_change_function_signature(validator_set_contract_session):
    contract = validator_set_contract_session

    signature = "finalizeChange()"

    try:
        contract.get_function_by_signature(signature)
    except ValueError:
        pytest.fail("no function with expected signature: " + signature)


def test_cannot_call_finalize_change(validator_set_contract_session, accounts):
    contract = validator_set_contract_session

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.finalizeChange().transact({"from": accounts[1]})


def test_change_validator_set_without_finalizing_do_not_touch_history(
    validator_set_contract_session, accounts
):
    assert (
        len(validator_set_contract_session.functions.getEpochStartHeights().call()) == 0
    )

    validator_set_contract_session.functions.testChangeValiatorSet(
        accounts[:2]
    ).transact()

    assert (
        len(validator_set_contract_session.functions.getEpochStartHeights().call()) == 0
    )


def test_finalize_change_stores_new_epoch_height(
    validator_set_contract_session, accounts, web3
):
    validator_set_contract_session.functions.testChangeValiatorSet(
        accounts[:2]
    ).transact()
    validator_set_contract_session.functions.testFinalizeChange().transact()

    assert validator_set_contract_session.functions.getEpochStartHeights().call() == [
        web3.eth.blockNumber
    ]


def test_finalize_change_stores_new_validator_set(
    validator_set_contract_session, accounts, web3
):
    new_validator_set = accounts[:2]
    validator_set_contract_session.functions.testChangeValiatorSet(
        new_validator_set
    ).transact()
    validator_set_contract_session.functions.testFinalizeChange().transact()

    assert (
        validator_set_contract_session.functions.getValidators(
            web3.eth.blockNumber
        ).call()
        == new_validator_set
    )


def test_cannot_call_initiate_change(
    validator_set_contract_session, accounts, validators
):
    contract = validator_set_contract_session

    with pytest.raises((eth_tester.exceptions.TransactionFailed, MismatchedABI)):
        contract.functions.initiateChange(validators).transact({"from": accounts[0]})


def test_report_validator_malicious_valdiator(
    validator_set_contract_session,
    malicious_validator_address,
    malicious_validator_key,
    validators,
):

    # Approve that the malicious validator is active before reporting.
    assert (
        validator_set_contract_session.functions.pendingValidators(2).call()
        == malicious_validator_address
    )

    timestamp = 100
    signed_block_header_one = make_block_header(
        timestamp=timestamp, private_key=malicious_validator_key
    )
    signed_block_header_two = make_block_header(
        timestamp=timestamp, private_key=malicious_validator_key
    )

    validator_set_contract_session.functions.reportMaliciousValidator(
        signed_block_header_one.unsignedBlockHeader,
        signed_block_header_one.signature,
        signed_block_header_two.unsignedBlockHeader,
        signed_block_header_two.signature,
    ).transact()

    assert (
        validator_set_contract_session.functions.pendingValidators(0).call()
        == validators[0]
    )

    assert (
        validator_set_contract_session.functions.pendingValidators(1).call()
        == validators[1]
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.pendingValidators(2).call()


def test_report_validator_malicious_non_validator(
    validator_set_contract_session, malicious_non_validator_key
):

    """Test a failing report of a malicious account.

    It is expected that the report fails, since the issuer of the blocks is not an
    validator and can't be removed.
    """

    timestamp = 100
    signed_block_header_one = make_block_header(
        timestamp=timestamp, private_key=malicious_non_validator_key
    )
    signed_block_header_two = make_block_header(
        timestamp=timestamp, private_key=malicious_non_validator_key
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.reportMaliciousValidator(
            signed_block_header_one.unsignedBlockHeader,
            signed_block_header_one.signature,
            signed_block_header_two.unsignedBlockHeader,
            signed_block_header_two.signature,
        ).transact()


def test_changing_validator_set_updates_proxy(
    validator_set_contract_session, validator_proxy_contract, validators, system_address
):
    assert validator_proxy_contract.functions.getValidators().call() == []
    validator_set_contract_session.functions.testChangeValiatorSet(validators).transact(
        {"from": system_address}
    )
    validator_set_contract_session.functions.finalizeChange().transact(
        {"from": system_address}
    )
    assert validator_proxy_contract.functions.getValidators().call() == validators
