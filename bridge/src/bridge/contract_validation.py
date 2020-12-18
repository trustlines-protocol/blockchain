import logging

import tenacity
from eth_utils import to_checksum_address
from web3 import Web3
from web3._utils.abi import abi_to_signature
from web3.contract import Contract

from bridge.contract_abis import MINIMAL_VALIDATOR_PROXY_ABI

logger = logging.getLogger(__name__)

retrying = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
)


def validate_contract_existence(contract: Contract) -> None:
    """Verifies if a given contract exists on the chain.

    It checks if any code is stored for the address. For events and functions
    in the ABI it will be checked if their signature hash can be found within
    the code. Throws an exception if the contract could not be verified. Else
    return nothing.
    """

    contract_code = retrying(contract.web3.eth.getCode)(contract.address)

    if not contract_code:
        raise ValueError(
            f"The given contract address {to_checksum_address(contract.address)} "
            f"does not point to a contract!"
        )

    for description in contract.abi:
        description_type = description.get("type", "function")

        if description_type in ("constructor", "fallback"):
            continue

        assert description_type in ("function", "event")

        signature = abi_to_signature(description)
        signature_hash = Web3.keccak(text=signature)

        if description_type == "function":
            description_exists_in_code = signature_hash[:4] in contract_code

        else:
            description_exists_in_code = signature_hash in contract_code

        if not description_exists_in_code:
            raise ValueError(
                f"The contract at the given address {to_checksum_address(contract.address)} does "
                f"not support the {description_type} with the following signature: {signature}!"
            )


def get_validator_proxy_contract(home_bridge_contract: Contract) -> Contract:
    validator_proxy_address = retrying(
        home_bridge_contract.functions.validatorProxy().call
    )()
    return home_bridge_contract.web3.eth.contract(
        address=validator_proxy_address, abi=MINIMAL_VALIDATOR_PROXY_ABI
    )


def is_bridge_validator(home_bridge_contract: Contract, address: bytes) -> bool:
    validator_proxy_contract = get_validator_proxy_contract(home_bridge_contract)
    return retrying(validator_proxy_contract.functions.isValidator(address).call)()
