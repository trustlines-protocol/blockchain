import json
import pkg_resources
from typing import Dict, NamedTuple

from web3.contract import Contract
from eth_keyfile import extract_key_from_keyfile
from deploy_tools.deploy import deploy_compiled_contract


class DeployedValidatorSetContracts(NamedTuple):
    set: Contract


def load_contracts_json() -> Dict:
    resource_package = __name__
    json_string = pkg_resources.resource_string(resource_package, "contracts.json")
    return json.loads(json_string)


def decrypt_private_key(keystore_path: str, password: str) -> bytes:
    return extract_key_from_keyfile(keystore_path, password.encode("utf-8"))


def build_transaction_options(*, gas, gas_price, nonce):

    transaction_options = {}

    if gas is not None:
        transaction_options["gas"] = gas
    if gas_price is not None:
        transaction_options["gasPrice"] = gas_price
    if nonce is not None:
        transaction_options["nonce"] = nonce

    return transaction_options


def deploy_validator_set_contracts(
    *, web3, transaction_options: Dict = None, private_key=None
) -> DeployedValidatorSetContracts:

    if transaction_options is None:
        transaction_options = {}

    compiled_contracts = load_contracts_json()

    validator_set_abi = compiled_contracts["ValidatorSet"]["abi"]
    validator_set_bin = compiled_contracts["ValidatorSet"]["bytecode"]

    validator_set_contract: Contract = deploy_compiled_contract(
        abi=validator_set_abi,
        bytecode=validator_set_bin,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )

    contracts = DeployedValidatorSetContracts(validator_set_contract)

    return contracts
