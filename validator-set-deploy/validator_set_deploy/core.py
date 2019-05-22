from typing import Dict, NamedTuple

from web3.contract import Contract
from deploy_tools.deploy import deploy_compiled_contract, load_contracts_json


class DeployedValidatorSetContracts(NamedTuple):
    set: Contract


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
