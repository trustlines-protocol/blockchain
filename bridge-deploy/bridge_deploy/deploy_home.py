import json
from typing import Dict, NamedTuple
from web3.contract import Contract
from deploy_tools.deploy import (
    deploy_compiled_contract,
    increase_transaction_options_nonce,
)


class DeployedHomeBridgeContracts(NamedTuple):
    home_bridge_storage: Contract
    home_bridge: Contract


def load_contract(contract_name):
    with open(
        f"../poa-bridge-contracts/build/contracts/{contract_name}.json"
    ) as json_file:
        return json.load(json_file)


def deploy_bridge_home_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):

    if transaction_options is None:
        transaction_options = {}

    eternal_storage_proxy_src = load_contract("EternalStorageProxy")

    home_bridge_storage_contract: Contract = deploy_compiled_contract(
        abi=eternal_storage_proxy_src["abi"],
        bytecode=eternal_storage_proxy_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    home_bridge_src = load_contract("HomeBridgeErcToNative")

    home_bridge_contract: Contract = deploy_compiled_contract(
        abi=home_bridge_src["abi"],
        bytecode=home_bridge_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    contracts = DeployedHomeBridgeContracts(
        home_bridge_storage_contract, home_bridge_contract
    )

    return contracts
