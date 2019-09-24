import pytest
from eth_utils import to_checksum_address

from validator_set_deploy.core import (
    deploy_validator_proxy_contract,
    deploy_validator_set_contract,
    initialize_validator_set_contract,
)

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


@pytest.fixture
def validator_set_contract(web3):

    validator_set_contract = deploy_validator_set_contract(web3=web3)

    return validator_set_contract


@pytest.fixture()
def initialized_validator_set_contract(web3, validator_list, validator_set_contract):
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
        validator_proxy_address=ZERO_ADDRESS,
    )

    checksummed_validator_list = [
        to_checksum_address(validator) for validator in validator_list
    ]

    assert validator_set_contract.functions.initialized().call() is True
    assert (
        validator_set_contract.functions.getValidators().call()
        == checksummed_validator_list
    )


def test_deploy_proxy(web3, accounts):

    proxy_contract = deploy_validator_proxy_contract(web3=web3, validators=accounts)

    assert proxy_contract.functions.getValidators().call() == accounts


def test_deploy_proxy_no_validators(web3):

    proxy_contract = deploy_validator_proxy_contract(web3=web3, validators=[])

    assert proxy_contract.functions.getValidators().call() == []
