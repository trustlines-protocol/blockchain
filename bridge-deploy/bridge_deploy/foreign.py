from typing import Dict, NamedTuple
from web3.contract import Contract
from deploy_tools.deploy import (
    deploy_compiled_contract,
    increase_transaction_options_nonce,
)

from bridge_deploy.utils import load_build_contract


class DeployedForeignBridgeResult(NamedTuple):
    foreign_bridge: Contract
    foreign_bridge_block_number: int


def deploy_foreign_bridge_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):

    if transaction_options is None:
        transaction_options = {}

    latest_block = web3.eth.getBlock("latest")

    foreign_bridge_src = load_build_contract("ForeignBridge")
    foreign_bridge_contract = deploy_compiled_contract(
        abi=foreign_bridge_src["abi"],
        bytecode=foreign_bridge_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    return DeployedForeignBridgeResult(foreign_bridge_contract, latest_block.number)
