from web3 import Web3
from web3.contract import Contract
from web3._utils.abi import abi_to_signature


def validate_contract(contract: Contract) -> None:
    """Verifies if a given contract exists on the chain.

    It checks if any code is stored for the address.
    For each entry in the ABI it will be checked if the signature hash can be
    found within the code.
    Throws an exception if the contract could not be verified. Else return
    nothing.
    """

    contract_code = contract.web3.eth.getCode(contract.address)

    if not contract_code:
        raise ValueError(
            f"The given contract address {contract.address} does not point to a contract!"
        )

    for entry in contract.abi:
        signature = abi_to_signature(entry)
        signature_hash = Web3.keccak(text=signature)

        if signature_hash not in contract_code:
            raise ValueError(
                f"The contract at the given address {contract.address}"
                f"does not support the following signature: {signature}!"
            )
