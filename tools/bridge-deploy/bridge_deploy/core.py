from typing import Dict
from web3 import Web3
from web3.contract import Contract
from deploy_tools.deploy import deploy_compiled_contract

from bridge_deploy.utils import load_build_contract


def deploy_foreign_bridge_contract(
    *,
    token_contract_address: str,
    web3: Web3,
    transaction_options: Dict = None,
    private_key=None
) -> Contract:

    if transaction_options is None:
        transaction_options = {}

    foreign_bridge_src = load_build_contract("ForeignBridge")

    return deploy_compiled_contract(
        abi=foreign_bridge_src["abi"],
        bytecode=foreign_bridge_src["bytecode"],
        constructor_args=(token_contract_address,),
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


def deploy_home_bridge_contract(
    *,
    validator_proxy_contract_address: str,
    validators_required_percent: int,
    web3: Web3,
    transaction_options: Dict = None,
    private_key=None
) -> Contract:

    if transaction_options is None:
        transaction_options = {}

    home_bridge_src = load_build_contract("HomeBridge")

    return deploy_compiled_contract(
        abi=home_bridge_src["abi"],
        bytecode=home_bridge_src["bytecode"],
        constructor_args=(
            validator_proxy_contract_address,
            validators_required_percent,
        ),
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
