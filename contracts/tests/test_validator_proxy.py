import pytest
import eth_tester.exceptions


def test_update_validators(validator_proxy_contract, validator_proxy_owner, accounts):
    validators = accounts[:5]
    validator_proxy_contract.functions.updateValidators(validators).transact(
        {"from": validator_proxy_owner}
    )


def test_update_validators_not_system(
    validator_proxy_contract, validator_proxy_owner, accounts
):
    validators = accounts[:5]
    sender = accounts[4]
    assert sender != validator_proxy_owner
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_proxy_contract.functions.updateValidators(validators).transact(
            {"from": sender}
        )


def test_number_of_validators(validator_proxy_with_validators, proxy_validators):
    assert validator_proxy_with_validators.functions.numberOfValidators().call() == len(
        proxy_validators
    )


def test_get_validators(validator_proxy_with_validators, proxy_validators):
    assert (
        validator_proxy_with_validators.functions.getValidators().call()
        == proxy_validators
    )


def test_is_validator(validator_proxy_with_validators, proxy_validators, accounts):
    for validator in proxy_validators:
        assert (
            validator_proxy_with_validators.functions.isValidator(validator).call()
            is True
        )

    non_validator = accounts[7]
    assert non_validator not in proxy_validators
    assert (
        validator_proxy_with_validators.functions.isValidator(non_validator).call()
        is False
    )
