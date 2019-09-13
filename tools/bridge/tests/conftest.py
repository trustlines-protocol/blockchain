import gevent.monkey
import gevent.pool
import pytest
import toml
from deploy_tools import deploy_compiled_contract
from eth_tester import EthereumTester
from gevent.queue import Queue
from web3 import EthereumTesterProvider, Web3
from web3.contract import Contract

import bridge.config

# check if gevent did it's monkeypatching
if "time" not in gevent.monkey.saved:
    raise RuntimeError(
        "cannot run bridge tests without gevent's monkeypatching, please use the pytest wrapper"
    )


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
def number_of_validators():
    """The total amount of validator accounts"""
    return 5


@pytest.fixture
def proxy_validator_accounts_and_keys(accounts, account_keys, number_of_validators):
    """Addresses and private keys of the validators in the proxy contract."""
    return accounts[:number_of_validators], account_keys[:number_of_validators]


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
def validator_account_and_key(proxy_validator_accounts_and_keys):
    """Address and private key of the validator running the confirmation sender."""
    accounts, keys = proxy_validator_accounts_and_keys
    return accounts[0], keys[0]


@pytest.fixture
def validator_address(validator_account_and_key):
    """Address of the validator running the confirmation sender."""
    account, _ = validator_account_and_key
    return account


@pytest.fixture
def non_validator_account_and_key(accounts, account_keys, number_of_validators):
    """Address and private key of an account which is not part of the validator set"""
    return accounts[number_of_validators], account_keys[number_of_validators]


@pytest.fixture
def non_validator_address(non_validator_account_and_key):
    """Address of an account which is not part of the validator set"""
    account, _ = non_validator_account_and_key
    return account


@pytest.fixture
def non_validator_key(non_validator_account_and_key):
    """Private key of an account which is not part of the validator set"""
    _, key = non_validator_account_and_key
    return key


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


@pytest.fixture
def write_config(tmp_path):
    """returns a function that writes a config file"""

    def write(config):
        p = tmp_path / "config.toml"
        with open(p, "w") as f:
            f.write(config)
        return str(p)

    return write


@pytest.fixture
def minimal_config():
    """return a minimal configuration"""

    return """
[foreign_chain]
rpc_url = "http://localhost:9200"
token_contract_address = "0x731a10897d267e19B34503aD902d0A29173Ba4B1"
bridge_contract_address = "0xb4c79daB8f259C7Aee6E5b2Aa729821864227e84"

[home_chain]
rpc_url = "http://localhost:9100"
bridge_contract_address = "0x771434486a221c6146F27B72fd160Bdf0eb1288e"

[validator_private_key]
raw = "0xb8dcbb8a564483279579e04bffacbd76f79df157cfbebed84079673b32d9e72f"
"""


@pytest.fixture
def webservice_config():
    """webservice part of the configuration"""
    return """
[webservice]
enabled = true
host = "127.0.0.1"
port = 9500
"""


@pytest.fixture
def load_config_from_string():
    """returns a function that loads a configuration dictionary from a string"""

    def load(s):
        return bridge.config.ConfigSchema().load(toml.loads(s))

    return load
