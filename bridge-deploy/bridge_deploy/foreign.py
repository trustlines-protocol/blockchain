from typing import Dict
from web3.contract import Contract
from deploy_tools.deploy import deploy_compiled_contract

from bridge_deploy.utils import load_build_contract


def deploy_foreign_bridge_contract(
    *, web3, transaction_options: Dict = None, private_key=None
) -> Contract:

    if transaction_options is None:
        transaction_options = {}

    foreign_bridge_src = load_build_contract("ForeignBridge")

    return deploy_compiled_contract(
        abi=foreign_bridge_src["abi"],
        bytecode=foreign_bridge_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
