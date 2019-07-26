from web3 import Web3
from web3.contract import Contract
from web3._utils.abi import abi_to_signature


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
            f"The given contract address {contract.address} does not point to a contract!"
        )

    for description in contract.abi:
        description_type = description.get("type", "function")

        if description_type in ("constructor", "fallback"):
            continue

        signature = abi_to_signature(description)
        signature_hash = Web3.keccak(text=signature)

        if description_type == "function":
            signature_hash = signature_hash[:4]

        if signature_hash not in contract_code:
            raise ValueError(
                f"The contract at the given address {contract.address} does not"
                f"support the {description_type} with the following signature: {signature}!"
            )
