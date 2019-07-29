from web3 import Web3
from web3.contract import Contract
from web3._utils.abi import abi_to_signature
from eth_utils import to_checksum_address

from bridge.contract_abis import MINIMAL_VALIDATOR_PROXY_ABI


def validate_contract(contract: Contract) -> None:
    """Verifies if a given contract exists on the chain.

    It checks if any code is stored for the address. For events and functions
    in the ABI it will be checked if their signature hash can be found within
    the code. Throws an exception if the contract could not be verified. Else
    return nothing.
    """

    contract_code = contract.web3.eth.getCode(contract.address)

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


def validate_confirmation_permissions(
    home_bridge_contract: Contract, address: str
) -> None:
    validator_proxy_address = home_bridge_contract.functions.validatorProxy().call()
    validator_proxy_contract = home_bridge_contract.web3.eth.contract(
        address=validator_proxy_address, abi=MINIMAL_VALIDATOR_PROXY_ABI
    )

    try:
        validate_contract(validator_proxy_contract)

    except ValueError as error:
        raise RuntimeError(
            f"Serious bridge setup error. The validator proxy contract at the address the home "
            f"bridge property points to does not exist or is not intact!"
        ) from error

    try:
        permission_status = validator_proxy_contract.functions.isValidator(
            address
        ).call()

    # Catch any type of error which could be raised by web3 on making the call.
    except Exception as error:
        raise RuntimeError(
            f"Something went wrong while trying to verify the signing accounts permission on the home bridge contract!"
        ) from error

    if not permission_status:
        raise ValueError(
            f"The address {address} is not a bridge validator to confirm transfers on the home bridge contract!"
        )
