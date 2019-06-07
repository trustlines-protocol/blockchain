import json
from typing import Dict, NamedTuple
from web3 import Account
from web3.contract import Contract
from deploy_tools.deploy import (
    deploy_compiled_contract,
    increase_transaction_options_nonce,
    send_function_call_transaction,
)


class DeployedHomeBridgeResult(NamedTuple):
    home_bridge: Contract
    home_bridge_block_number: int


def load_contract(contract_name):
    with open(
        f"../poa-bridge-contracts/build/contracts/{contract_name}.json"
    ) as json_file:
        return json.load(json_file)


def deploy_home_bridge_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):

    if transaction_options is None:
        transaction_options = {}

    latest_block = web3.eth.getBlock("latest")

    # Deploy home bridge proxy
    eternal_storage_proxy_src = load_contract("EternalStorageProxy")
    home_bridge_storage_contract = deploy_compiled_contract(
        abi=eternal_storage_proxy_src["abi"],
        bytecode=eternal_storage_proxy_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    # Deploy home bridge implementation
    home_bridge_src = load_contract("HomeBridgeErcToNative")
    home_bridge_contract = deploy_compiled_contract(
        abi=home_bridge_src["abi"],
        bytecode=home_bridge_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    # Connect home bridge proxy to implementation
    home_bridge_storage_upgrade = home_bridge_storage_contract.functions.upgradeTo(
        1, home_bridge_contract.address
    )
    send_function_call_transaction(
        home_bridge_storage_upgrade,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    # Use proxy from now on
    home_bridge_contract = web3.eth.contract(
        abi=home_bridge_src["abi"], address=home_bridge_storage_contract.address
    )

    contracts = DeployedHomeBridgeResult(home_bridge_contract, latest_block.number)

    return contracts


def initialize_home_bridge_contract(
    *,
    web3,
    transaction_options: Dict = None,
    home_bridge_contract,
    validator_contract_address,
    home_daily_limit,
    home_max_per_tx,
    home_min_per_tx,
    home_gas_price,
    required_block_confirmations,
    block_reward_address,
    private_key=None,
):
    if transaction_options is None:
        transaction_options = {}

    home_bridge_contract_initialize = home_bridge_contract.functions.initialize(
        validator_contract_address,
        home_daily_limit,  # 30000000000000000000000000,  # HOME_DAILY_LIMIT in WEI,
        home_max_per_tx,  # 1500000000000000000000000,  # HOME_MAX_AMOUNT_PER_TX in WEI,
        home_min_per_tx,  # 500000000000000000,  # HOME_MIN_AMOUNT_PER_TX in WEI,
        home_gas_price,  # 1000000000,  # HOME_GAS_PRICE in WEI,
        required_block_confirmations,  # 4,  # HOME_REQUIRED_BLOCK_CONFIRMATIONS,
        block_reward_address,  # "0x0000000000000000000000000000000000000000",  # BLOCK_REWARD_ADDRESS,
        1,  # 15000000000000000000000000,  # FOREIGN_DAILY_LIMIT,
        0,  # 750000000000000000000000,  # FOREIGN_MAX_AMOUNT_PER_TX,
        Account.privateKeyToAccount(
            private_key
        ).address,  # "0x0000000000000000000000000000000000000000",  # HOME_BRIDGE_OWNER
    )
    send_function_call_transaction(
        home_bridge_contract_initialize,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    # TODO: transfer ownership
