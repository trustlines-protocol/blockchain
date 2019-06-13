from typing import Dict, NamedTuple
from web3.contract import Contract
from web3.eth import Account
from deploy_tools.deploy import (
    deploy_compiled_contract,
    increase_transaction_options_nonce,
    send_function_call_transaction,
)

from bridge_deploy.utils import load_poa_contract, load_build_contract


class DeployedHomeBridgeResult(NamedTuple):
    home_bridge: Contract
    home_bridge_proxy: Contract
    home_bridge_block_number: int


def deploy_home_block_reward_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):
    if transaction_options is None:
        transaction_options = {}

    block_reward_src = load_build_contract("RewardByBlock", file_name="reward")

    block_reward_contract = deploy_compiled_contract(
        abi=block_reward_src["abi"],
        bytecode=block_reward_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    return block_reward_contract


def deploy_home_bridge_validators_contract(
    *,
    web3,
    transaction_options: Dict = None,
    validator_proxy,
    required_signatures_divisor,
    required_signatures_multiplier,
    private_key=None,
):
    if transaction_options is None:
        transaction_options = {}

    bridge_validators_src = load_build_contract("BridgeValidators")

    bridge_validators_contract = deploy_compiled_contract(
        abi=bridge_validators_src["abi"],
        bytecode=bridge_validators_src["bytecode"],
        constructor_args=(
            validator_proxy,
            required_signatures_divisor,
            required_signatures_multiplier,
        ),
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    return bridge_validators_contract


def deploy_home_bridge_contract(
    *, web3, transaction_options: Dict = None, private_key=None
):

    if transaction_options is None:
        transaction_options = {}

    latest_block = web3.eth.getBlock("latest")

    # Deploy home bridge proxy
    eternal_storage_proxy_src = load_poa_contract("EternalStorageProxy")
    home_bridge_storage_contract = deploy_compiled_contract(
        abi=eternal_storage_proxy_src["abi"],
        bytecode=eternal_storage_proxy_src["bytecode"],
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    # Deploy home bridge implementation
    home_bridge_src = load_poa_contract("HomeBridgeErcToNative")
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

    contracts = DeployedHomeBridgeResult(
        home_bridge_contract, home_bridge_storage_contract, latest_block.number
    )

    return contracts


def initialize_home_bridge_contract(
    *,
    web3,
    transaction_options: Dict = None,
    home_bridge_contract,
    home_bridge_proxy_contract,
    validator_contract_address,
    home_daily_limit,
    home_max_per_tx,
    home_min_per_tx,
    home_gas_price,
    required_block_confirmations,
    block_reward_address,
    owner_address=None,
    private_key=None,
):
    if transaction_options is None:
        transaction_options = {}

    if owner_address is None:
        if private_key is not None:
            owner_address = Account.privateKeyToAccount(private_key)

    home_bridge_contract_initialize = home_bridge_contract.functions.initialize(
        validator_contract_address,
        home_daily_limit,
        home_max_per_tx,
        home_min_per_tx,
        home_gas_price,
        required_block_confirmations,
        block_reward_address,
        1,  # FOREIGN_DAILY_LIMIT,
        0,  # FOREIGN_MAX_AMOUNT_PER_TX,
        owner_address,  # OWNER
    )

    send_function_call_transaction(
        home_bridge_contract_initialize,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    home_bridge_contract_set_execution_daily_limit = home_bridge_contract.functions.setExecutionDailyLimit(
        0
    )
    send_function_call_transaction(
        home_bridge_contract_set_execution_daily_limit,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    home_bridge_proxy_contract_transfer_proxy_ownership = home_bridge_proxy_contract.functions.transferProxyOwnership(
        "0x0000000000000000000000000000000000000001"
    )
    send_function_call_transaction(
        home_bridge_proxy_contract_transfer_proxy_ownership,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)
