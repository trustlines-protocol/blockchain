import pytest

from eth_tester import EthereumTester
from web3 import Web3, EthereumTesterProvider
from web3.contract import Contract
from gevent.queue import Queue
import gevent.pool
from deploy_tools import deploy_compiled_contract


@pytest.fixture()
def pool():
    """return a gevent pool object.

    it will call kill all greenlets in the pool after the test has finished
    """
    p = gevent.pool.Pool()
    yield p
    p.kill(timeout=0.5)


@pytest.fixture()
def spawn(pool):
    """spawn a greenlet
    it will be automatically killed after the test run
    """
    return pool.spawn


@pytest.fixture
def tester_foreign():
    """EthereumTester instance in charge of the foreign chain."""
    return EthereumTester()


@pytest.fixture
def tester_home():
    """EthereumTester instance in charge of the home chain."""
    return EthereumTester()


@pytest.fixture
def w3_foreign(tester_foreign):
    """Web3 instance connected to the foreign chain."""
    provider = EthereumTesterProvider(tester_foreign)
    return Web3(provider)


@pytest.fixture
def w3_home(tester_home):
    """Web3 instance connected to the home chain."""
    provider = EthereumTesterProvider(tester_home)
    return Web3(provider)


@pytest.fixture
def transfer_event_queue():
    return Queue()


@pytest.fixture
def premint_token_address(accounts):
    """An address whose account on the foreign chain has been endowed with some tokens."""
    return accounts[0]


@pytest.fixture
def deploy_contract_on_chain(contract_assets):
    """A function that deploys a contract on a chain specified via a web3 instance."""

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
    """The token contract on the foreign chain."""
    constructor_args = (
        "Trustlines Network Token",
        "TLN",
        18,
        premint_token_address,
        1_000_000,
    )

    return deploy_contract_on_chain(
        w3_foreign, "TrustlinesNetworkToken", constructor_args=constructor_args
    )


@pytest.fixture
def foreign_bridge_contract(deploy_contract_on_chain, w3_foreign, token_contract):
    """The foreign bridge contract."""
    return deploy_contract_on_chain(
        w3_foreign, "ForeignBridge", constructor_args=(token_contract.address,)
    )


@pytest.fixture
def proxy_validator_accounts_and_keys(accounts, account_keys):
    """Addresses and private keys of the validators in the proxy contract."""
    num_validators = 5
    return accounts[:num_validators], account_keys[:num_validators]


@pytest.fixture
def proxy_validators(proxy_validator_accounts_and_keys):
    """Addresses of the validators in the proxy contract."""
    accounts, _ = proxy_validator_accounts_and_keys
    return accounts


@pytest.fixture
def proxy_validator_keys(proxy_validator_accounts_and_keys):
    """Private keys of the validators in the proxy contract."""
    _, keys = proxy_validator_accounts_and_keys
    return keys


@pytest.fixture
def system_address(accounts):
    """Address pretending to be the system address."""
    return accounts[0]


@pytest.fixture
def validator_proxy_contract(deploy_contract_on_chain, w3_home, system_address):
    """The plain validator proxy contract."""
    contract = deploy_contract_on_chain(
        w3_home, "TestValidatorProxy", constructor_args=([], system_address)
    )

    assert contract.functions.systemAddress().call() == system_address

    return contract


@pytest.fixture
def validator_proxy_with_validators(
    validator_proxy_contract, system_address, proxy_validators
):
    """Validator proxy contract using the proxy validators."""
    validator_proxy_contract.functions.updateValidators(proxy_validators).transact(
        {"from": system_address}
    )
    return validator_proxy_contract


@pytest.fixture
def home_bridge_contract(
    deploy_contract_on_chain, validator_proxy_with_validators, w3_home, tester_home
):
    """The home bridge contract."""
    contract = deploy_contract_on_chain(
        w3_home,
        "HomeBridge",
        constructor_args=(validator_proxy_with_validators.address, 50),
    )

    account_0 = tester_home.get_accounts()[0]

    tester_home.send_transaction(
        {"from": account_0, "to": contract.address, "gas": 100_000, "value": 1_000_000}
    )

    return contract
