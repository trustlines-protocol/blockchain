#! pytest

import pytest
import eth_tester.exceptions
from web3.exceptions import MismatchedABI


def test_get_validator(validator_set_contract_session, validators):

    assert validator_set_contract_session.functions.getValidators().call() == validators


def test_init_already_initialized(validator_set_contract_session, accounts):
    """verifies that we cannot call the init function twice"""

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.init([accounts[0]]).transact({"from": accounts[0]})


def test_remove_validator1(validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[1]).transact({"from": accounts[0]})
    assert contract.functions.pendingValidators(0).call() == validators[0]
    assert contract.functions.pendingValidators(1).call() == validators[2]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.pendingValidators(2).call()


def test_remove_validator0(validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact({"from": accounts[0]})
    # Mind that deleting an entry from the array replace the index to remove
    # with the last entry of the array and cut of the last index afterwards.
    assert contract.functions.pendingValidators(0).call() == validators[2]
    assert contract.functions.pendingValidators(1).call() == validators[1]
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.pendingValidators(2).call()


def test_remove_validator_not_finalized(validator_set_contract_session, validators, accounts):
    """verifies that we cannot remove a validator when the set of validator is not finalized"""
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[1]).transact({"from": accounts[0]})
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testRemoveValidator(validators[0]).transact({"from": accounts[0]})


def test_removing_validator_emits_initiate_change_event(
        validator_set_contract_session,
        validators,
        accounts):

    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact({"from": accounts[0]})

    assert len(contract.events.InitiateChange.createFilter(fromBlock=0).get_all_entries()) == 1


def test_initiate_change_event_parent_hash(web3, validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact({"from": accounts[0]})

    latest_block_number = web3.eth.getBlock('latest')['number']
    parent_hash_of_latest_block = web3.eth.getBlock(latest_block_number - 1)['hash']
    parent_hash_of_event = contract.events.InitiateChange.createFilter(
        fromBlock=0).get_all_entries()[0]["args"]['_parentHash']

    assert parent_hash_of_event == parent_hash_of_latest_block


def test_initiate_change_event_new_set(validator_set_contract_session, validators, accounts):
    contract = validator_set_contract_session

    contract.functions.testRemoveValidator(validators[0]).transact({"from": accounts[0]})

    pending_validator_in_contract = contract.functions.pendingValidators(0).call()

    new_set = contract.events.InitiateChange.createFilter(
        fromBlock=0).get_all_entries()[0]["args"]['_newSet'][0]

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
        contract.functions.finalizeChange().transact({"from": accounts[0]})


def test_cannot_call_initiate_change(validator_set_contract_session, accounts, validators):
    contract = validator_set_contract_session

    with pytest.raises((eth_tester.exceptions.TransactionFailed, MismatchedABI)):
        contract.functions.initiateChange(validators).transact({"from": accounts[0]})


def test_report_validator_malicious_valdiator(
        validator_set_contract_session,
        sign_two_equivocating_block_header,
        malicious_validator_address,
        malicious_validator_key,
        validators):

    """Test a complete successful report of a malicious validator.

    Since the issued blocks from the Koven test network have used the same address for the signing
    the block as well as getting the reward, it is possible to compare the outcome of the recovery
    with the content of the block header.
    """

    # Approve that the malicious validator is active before reporting.
    assert (validator_set_contract_session.functions.pendingValidators(2).call() ==
            malicious_validator_address)

    two_signed_blocks_equivocated_by_malicious_validator = (
        sign_two_equivocating_block_header(malicious_validator_key)
    )

    validator_set_contract_session.functions.reportMaliciousValidator(
            two_signed_blocks_equivocated_by_malicious_validator[0].unsignedBlockHeader,
            two_signed_blocks_equivocated_by_malicious_validator[0].signature,
            two_signed_blocks_equivocated_by_malicious_validator[1].unsignedBlockHeader,
            two_signed_blocks_equivocated_by_malicious_validator[1].signature).transact()

    assert (validator_set_contract_session.functions.pendingValidators(0).call() ==
            validators[0])

    assert (validator_set_contract_session.functions.pendingValidators(1).call() ==
            validators[1])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.pendingValidators(2).call()


def test_report_validator_malicious_non_validator(
        validator_set_contract_session,
        sign_two_equivocating_block_header,
        malicious_non_validator_key):

    """Test a failing report of a malicious account.

    It is expected that the report fails, since the issuer of the blocks is not an
    validator and can't be removed.
    """

    two_signed_blocks_equivocated_by_malicious_non_validator = (
        sign_two_equivocating_block_header(malicious_non_validator_key)
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_set_contract_session.functions.reportMaliciousValidator(
                two_signed_blocks_equivocated_by_malicious_non_validator[0].unsignedBlockHeader,
                two_signed_blocks_equivocated_by_malicious_non_validator[0].signature,
                two_signed_blocks_equivocated_by_malicious_non_validator[1].unsignedBlockHeader,
                two_signed_blocks_equivocated_by_malicious_non_validator[1].signature).transact()
