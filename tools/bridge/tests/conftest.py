import pytest

from eth_tester import EthereumTester
from web3 import Web3, EthereumTesterProvider


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
