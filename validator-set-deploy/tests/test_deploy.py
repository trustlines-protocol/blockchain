import pytest

from eth_utils import to_checksum_address

from validator_set_deploy.core import (
    deploy_validator_set_contract,
    initialize_validator_set_contract,
)


@pytest.fixture
def validator_set_contract(web3):

    validator_set_contract = deploy_validator_set_contract(web3=web3)

    return validator_set_contract


def test_deploy_validator_set(web3):

    validator_set_contract = deploy_validator_set_contract(web3=web3)

    system_address = "0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE"
    assert validator_set_contract.functions.systemAddress().call() == system_address
    assert validator_set_contract.functions.initialized().call() is False


def test_init_validator_set(validator_set_contract, validator_list, web3):

    initialize_validator_set_contract(
        web3=web3,
        validator_set_contract=validator_set_contract,
        validators=validator_list,
    )

    checksummed_validator_list = [
        to_checksum_address(validator) for validator in validator_list
    ]

    assert validator_set_contract.functions.initialized().call() is True
    assert (
        validator_set_contract.functions.getValidators().call()
        == checksummed_validator_list
    )
