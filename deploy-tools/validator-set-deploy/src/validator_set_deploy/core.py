from typing import Dict

from deploy_tools.deploy import (
    deploy_compiled_contract,
    load_contracts_json,
    send_function_call_transaction,
)
from web3.contract import Contract


def deploy_validator_set_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):

    if transaction_options is None:
        transaction_options = {}

    compiled_contracts = load_contracts_json(__name__)

    validator_set_abi = compiled_contracts["ValidatorSet"]["abi"]
    validator_set_bin = compiled_contracts["ValidatorSet"]["bytecode"]

    validator_set_contract: Contract = deploy_compiled_contract(
        abi=validator_set_abi,
        bytecode=validator_set_bin,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )

    return validator_set_contract


def initialize_validator_set_contract(
    *,
    web3,
    transaction_options=None,
    validator_set_contract,
    validators,
    validator_proxy_address,
    private_key=None
) -> None:
    if transaction_options is None:
        transaction_options = {}

    validator_init = validator_set_contract.functions.init(
        validators, validator_proxy_address
    )

    send_function_call_transaction(
        validator_init,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


def deploy_validator_proxy_contract(
    *, web3, transaction_options: Dict = None, private_key=None, validators
):

    if transaction_options is None:
        transaction_options = {}

    compiled_contracts = load_contracts_json(__name__)

    validator_proxy_abi = compiled_contracts["ValidatorProxy"]["abi"]
    validator_proxy_bin = compiled_contracts["ValidatorProxy"]["bytecode"]

    validator_proxy_contract: Contract = deploy_compiled_contract(
        abi=validator_proxy_abi,
        bytecode=validator_proxy_bin,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
        constructor_args=(validators,),
    )

    return validator_proxy_contract


def get_validator_contract(*, web3, address):

    validator_contract_abi = load_contracts_json(__name__)["ValidatorSet"]["abi"]

    return web3.eth.contract(address=address, abi=validator_contract_abi)
