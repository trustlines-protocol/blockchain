#! pytest

import pytest
import eth_tester.exceptions
from .data_generation import make_block_header


def test_init_already_initialized(validator_slasher_contract, accounts):
    """verifies that we cannot call the init function twice"""
    contract = validator_slasher_contract
    fund_contract_address = accounts[0]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(fund_contract_address).transact({"from": accounts[0]})


def test_init_not_owner(
    non_initialized_validator_slasher_contract_session, accounts, validators
):
    contract = non_initialized_validator_slasher_contract_session
    fund_contract_address = accounts[0]

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.init(fund_contract_address).transact({"from": accounts[1]})


def test_report_malicious_validator_malicious_validator(
    validator_slasher_contract,
    deposit_locker_contract_with_deposits,
    malicious_validator_address,
    malicious_validator_key,
):

    """Test a complete successful report of a malicious validator.

    It is expected that the report runs successfully through.
    Afterwards the malicious validator's deposit should be empty.
    """

    assert deposit_locker_contract_with_deposits.functions.canWithdraw(
        malicious_validator_address
    ).call()

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

    assert not deposit_locker_contract_with_deposits.functions.canWithdraw(
        malicious_validator_address
    ).call()


def test_report_malicious_validator_malicious_non_validator(
    validator_slasher_contract, malicious_non_validator_key
):

    """Test a failing report of a malicious non validator.

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
        validator_slasher_contract.functions.reportMaliciousValidator(
            signed_block_header_one.unsignedBlockHeader,
            signed_block_header_one.signature,
            signed_block_header_two.unsignedBlockHeader,
            signed_block_header_two.signature,
        ).transact()
