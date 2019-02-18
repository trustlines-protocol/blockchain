#! pytest

import pytest
import eth_tester.exceptions


def test_init_already_initialized(validator_slasher_contract, accounts):
    """verifies that we cannot call the init function twice"""
    contract = validator_slasher_contract
    fund_contract_address = accounts[0]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init([accounts[0]], fund_contract_address).transact(
            {"from": accounts[0]}
        )


def test_init_not_owner(
    non_initialised_validator_slasher_contract_session, accounts, validators
):
    contract = non_initialised_validator_slasher_contract_session
    fund_contract_address = accounts[0]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(validators, fund_contract_address).transact(
            {"from": accounts[1]}
        )


def test_remove_validator1(validator_slasher_contract, validators, accounts):
    contract = validator_slasher_contract

    contract.functions.testRemoveValidatorFromSet(validators[1]).transact(
        {"from": accounts[0]}
    )
    assert contract.functions.getValidator(0).call() == validators[0]
    assert contract.functions.getValidator(1).call() == validators[2]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.getValidator(2).call()


def test_remove_validator0(validator_slasher_contract, validators, accounts):
    contract = validator_slasher_contract

    contract.functions.testRemoveValidatorFromSet(validators[0]).transact(
        {"from": accounts[0]}
    )
    # Mind that deleting an entry from the array replace the index to remove
    # with the last entry of the array and cut of the last index afterwards.
    assert contract.functions.getValidator(0).call() == validators[2]
    assert contract.functions.getValidator(1).call() == validators[1]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.getValidator(2).call()


def test_report_malicious_validator_malicious_validator(
    validator_slasher_contract,
    deposit_locker_contract_with_deposits,
    sign_two_equivocating_block_header,
    malicious_validator_address,
    malicious_validator_key,
    deposit_amount,
    validators,
):

    """Test a complete successful report of a malicious validator.

    It is expected that the report runs successfully through.
    Afterwards the malicious validator must be not in the list anymore,
    as well as his deposit should be empty.
    """

    assert (
        deposit_locker_contract_with_deposits.functions.deposits(
            malicious_validator_address
        ).call()
        == deposit_amount
    )

    assert (
        validator_slasher_contract.functions.getValidator(2).call()
        == malicious_validator_address
    )

    two_signed_blocks_equivocated_by_malicious_validator = sign_two_equivocating_block_header(
        malicious_validator_key
    )

    # Approve that the malicious validator is active before reporting.
    validator_slasher_contract.functions.reportMaliciousValidator(
        two_signed_blocks_equivocated_by_malicious_validator[0].unsignedBlockHeader,
        two_signed_blocks_equivocated_by_malicious_validator[0].signature,
        two_signed_blocks_equivocated_by_malicious_validator[1].unsignedBlockHeader,
        two_signed_blocks_equivocated_by_malicious_validator[1].signature,
    ).transact()

    assert (
        deposit_locker_contract_with_deposits.functions.deposits(
            malicious_validator_address
        ).call()
        == 0
    )

    assert validator_slasher_contract.functions.getValidator(0).call() == validators[0]

    assert validator_slasher_contract.functions.getValidator(1).call() == validators[1]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_slasher_contract.functions.getValidator(2).call()


def test_report_malicious_validator_malicious_non_validator(
    validator_slasher_contract,
    deposit_locker_contract,
    sign_two_equivocating_block_header,
    malicious_non_validator_key,
):

    """Test a failing report of a malicious non validator.

    It is expected that the report fails, since the issuer of the blocks is not an
    validator and can't be removed.
    """

    two_signed_blocks_equivocated_by_malicious_non_validator = sign_two_equivocating_block_header(
        malicious_non_validator_key
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_slasher_contract.functions.reportMaliciousValidator(
            two_signed_blocks_equivocated_by_malicious_non_validator[
                0
            ].unsignedBlockHeader,
            two_signed_blocks_equivocated_by_malicious_non_validator[0].signature,
            two_signed_blocks_equivocated_by_malicious_non_validator[
                1
            ].unsignedBlockHeader,
            two_signed_blocks_equivocated_by_malicious_non_validator[1].signature,
        ).transact()
