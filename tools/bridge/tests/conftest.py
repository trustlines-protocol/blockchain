import pytest

from eth_tester import EthereumTester
from web3 import Web3, EthereumTesterProvider
from web3.contract import Contract
from gevent.queue import Queue
from deploy_tools import deploy_compiled_contract


@pytest.fixture
def tester_foreign():
    return EthereumTester()


@pytest.fixture
def tester_home():
    return EthereumTester()


@pytest.fixture
def w3_foreign(tester_foreign):
    provider = EthereumTesterProvider(tester_foreign)
    return Web3(provider)


@pytest.fixture
def w3_home(tester_home):
    provider = EthereumTesterProvider(tester_home)
    return Web3(provider)


@pytest.fixture
def token_transfer_event_queue():
    return Queue()


@pytest.fixture
def premint_token_address(accounts):
    return accounts[0]


@pytest.fixture
def deploy_contract_on_chain(contract_assets):
    def deploy(
        web3: Web3, contract_identifier: str, *, constructor_args=()
    ) -> Contract:
        return deploy_compiled_contract(
            abi=contract_assets[contract_identifier]["abi"],
            bytecode=contract_assets[contract_identifier]["bytecode"],
            web3=web3,
            constructor_args=constructor_args,
        )

    return deploy


@pytest.fixture
def token_contract(deploy_contract_on_chain, w3_foreign, premint_token_address):
    constructor_args = (
        "Trustlines Network Token",
        "TLN",
        18,
        premint_token_address,
        1000000,
    )

    return deploy_contract_on_chain(
        w3_foreign, "TrustlinesNetworkToken", constructor_args=constructor_args
    )


@pytest.fixture
def foreign_bridge_contract(deploy_contract_on_chain, w3_foreign, token_contract):
    return deploy_contract_on_chain(
        w3_foreign, "ForeignBridge", constructor_args=(token_contract.address,)
    )
