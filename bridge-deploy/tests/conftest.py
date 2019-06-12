import pytest
import eth_tester

from bridge_deploy.home import (
    deploy_home_block_reward_contract,
    deploy_home_bridge_validators_contract,
    deploy_home_bridge_contract,
)

# increase eth_tester's GAS_LIMIT
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6


@pytest.fixture
def block_reward_contract(web3):
    reward_contract = deploy_home_block_reward_contract(web3=web3)
    return reward_contract


@pytest.fixture
def home_bridge_validators_contract(web3):
    home_bridge_validators_contract = deploy_home_bridge_validators_contract(
        web3=web3,
        validator_proxy="0x0000000000000000000000000000000000000000",
        required_signatures_divisor=1,
        required_signatures_multiplier=1,
    )
    return home_bridge_validators_contract


@pytest.fixture
def home_bridge_deployment_result(web3):
    deployment_result = deploy_home_bridge_contract(web3=web3)
    return deployment_result


@pytest.fixture
def home_bridge_contract(home_bridge_deployment_result):
    return home_bridge_deployment_result.home_bridge


@pytest.fixture
def home_bridge_proxy_contract(home_bridge_deployment_result):
    return home_bridge_deployment_result.home_bridge_proxy
