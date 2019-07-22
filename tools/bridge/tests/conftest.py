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
def transfer_event_queue():
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


@pytest.fixture
def proxy_validator_accounts_and_keys(accounts, account_keys):
    num_validators = 5
    return accounts[:num_validators], account_keys[:num_validators]


@pytest.fixture
def proxy_validators(proxy_validator_accounts_and_keys):
    accounts, _ = proxy_validator_accounts_and_keys
    return accounts


@pytest.fixture
def proxy_validator_keys(proxy_validator_accounts_and_keys):
    _, keys = proxy_validator_accounts_and_keys
    return keys


@pytest.fixture
def system_address(accounts):
    return accounts[0]


@pytest.fixture
def validator_proxy_contract(
    deploy_contract_on_chain, w3_home, system_address, accounts
):
    contract = deploy_contract_on_chain(
        w3_home, "TestValidatorProxy", constructor_args=([], system_address)
    )

    assert contract.functions.systemAddress().call() == system_address

    return contract


@pytest.fixture
def validator_proxy_with_validators(
    validator_proxy_contract, system_address, proxy_validators
):
    validator_proxy_contract.functions.updateValidators(proxy_validators).transact(
        {"from": system_address}
    )
    return validator_proxy_contract


@pytest.fixture
def home_bridge_contract(
    deploy_contract_on_chain, validator_proxy_with_validators, w3_home, tester_home
):
    contract = deploy_contract_on_chain(
        w3_home,
        "TestHomeBridge",
        constructor_args=(validator_proxy_with_validators.address, 50),
    )

    account_0 = tester_home.get_accounts()[0]

    tester_home.send_transaction(
        {"from": account_0, "to": contract.address, "gas": 100000, "value": 1_000_000}
    )

    return contract
