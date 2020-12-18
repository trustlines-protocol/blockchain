import pytest

from bridge.contract_abis import HOME_BRIDGE_ABI
from bridge.contract_validation import is_bridge_validator, validate_contract_existence

FAKE_ERC20_TOKEN_ABI = [
    {"anonymous": False, "inputs": [], "name": "FakeEvent", "type": "event"}
]


@pytest.fixture
def internal_home_bridge_contract(w3_home, home_bridge_contract):
    """Home bridge contract as it would be represented within the client.

    Using the home bridge instead of the token, because the to check internal
    ABI is more complex and contain not only descriptions of type 'event'.
    """
    return w3_home.eth.contract(
        address=home_bridge_contract.address, abi=HOME_BRIDGE_ABI
    )


def test_validate_contract_existence_successfully(internal_home_bridge_contract):
    validate_contract_existence(internal_home_bridge_contract)


def test_validate_contract_existence_undeployed_address(internal_home_bridge_contract):
    internal_home_bridge_contract.address = "0x0000000000000000000000000000000000000000"

    with pytest.raises(ValueError):
        validate_contract_existence(internal_home_bridge_contract)


def test_validate_contract_existence_not_matching_abi(internal_home_bridge_contract):
    internal_home_bridge_contract.abi = FAKE_ERC20_TOKEN_ABI

    with pytest.raises(ValueError):
        validate_contract_existence(internal_home_bridge_contract)


def test_validate_confirmation_permissions_successfully(
    home_bridge_contract, validator_address
):
    assert is_bridge_validator(home_bridge_contract, validator_address)


def test_validate_confirmation_permissions_not_permissioned(
    home_bridge_contract, non_validator_address
):
    assert not is_bridge_validator(home_bridge_contract, non_validator_address)
