from typing import Dict
import csv

from web3.contract import Contract
from deploy_tools.deploy import (
    deploy_compiled_contract,
    load_contracts_json,
    send_function_call_transaction,
)
from eth_utils import is_address, to_checksum_address


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
    private_key=None,
) -> None:
    if transaction_options is None:
        transaction_options = {}

    validator_init = validator_set_contract.functions.init(validators)

    send_function_call_transaction(
        validator_init,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


def deploy_validator_proxy_contract(
    *,
    web3,
    transaction_options: Dict = None,
    private_key=None,
    validator_contract_address,
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
        constructor_args=(validator_contract_address,),
    )

    return validator_proxy_contract


def get_validator_contract(*, web3, address):

    validator_contract_abi = load_contracts_json(__name__)["ValidatorSet"]["abi"]

    return web3.eth.contract(address=address, abi=validator_contract_abi)


def read_addresses_in_csv(file_path: str):  # TODO: refactor this into deploy_tools
    with open(file_path) as f:
        reader = csv.reader(f)
        addresses = []
        for line in reader:
            address = validate_and_format_address(line[0])
            addresses.append(address)
        return addresses


def validate_and_format_address(address):  # TODO: refactor this into deploy_tools
    """Validates the address and formats it into the internal format
    Will raise `InvalidAddressException, if the address is invalid"""
    if is_address(address):
        return to_checksum_address(address)
    else:
        raise InvalidAddressException()


class InvalidAddressException(Exception):  # TODO: refactor this into deploy_tools
    pass
