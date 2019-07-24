import pytest

from bridge.contract_validator import validate_contract
from bridge.contract_abis import MINIMAL_ERC20_TOKEN_ABI


FAKE_ERC20_TOKEN_ABI = [
    {"anonymous": False, "inputs": [], "name": "FakeEvent", "type": "event"}
]


@pytest.fixture()
def internal_token_contract(w3_foreign, token_contract):
    """Token contract as it would be represented within the client."""
    return w3_foreign.eth.contract(
        address=token_contract.address, abi=MINIMAL_ERC20_TOKEN_ABI
    )


def test_validate_contract_successfully(internal_token_contract):
    validate_contract(internal_token_contract)


def test_validate_contract_undeployed_address(internal_token_contract):
    internal_token_contract.address = "0x0000000000000000000000000000000000000000"

    with pytest.raises(ValueError):
        validate_contract(internal_token_contract)


def test_validate_contract_not_matching_abi(internal_token_contract):
    internal_token_contract.abi = FAKE_ERC20_TOKEN_ABI

    with pytest.raises(ValueError):
        validate_contract(internal_token_contract)
