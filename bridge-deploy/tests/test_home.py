import pytest
from bridge_deploy.home import (
    deploy_home_bridge_contract,
    initialize_home_bridge_contract,
)


@pytest.fixture
def home_bridge_contract(web3):
    deployment_result = deploy_home_bridge_contract(web3=web3)
    home_bridge_contract = deployment_result.home_bridge
    return home_bridge_contract


def test_deploy_home_bridge_contract(web3):

    deployment_result = deploy_home_bridge_contract(web3=web3)
    home_bridge_contract = deployment_result.home_bridge

    assert home_bridge_contract.functions.getBridgeInterfacesVersion().call() == [
        2,
        2,
        0,
    ]


def test_initialize_home_bridge_contract(home_bridge_contract, web3):
    initialize_home_bridge_contract(
        web3=web3,
        home_bridge_contract=home_bridge_contract,
        validator_contract_address="0x0000000000000000000000000000000000000002",
        home_daily_limit=30000000000000000000000000,
        home_max_per_tx=1500000000000000000000000,
        home_min_per_tx=500000000000000000,
        home_gas_price=1000000000,
        required_block_confirmations=1,
        block_reward_address="0x0000000000000000000000000000000000000002",
    )

    assert home_bridge_contract.functions.isInitialized().call()
