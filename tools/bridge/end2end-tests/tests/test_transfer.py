import subprocess
import time
import warnings
from subprocess import Popen

import pytest
import requests
import toml
from deploy_tools import deploy_compiled_contract
from deploy_tools.deploy import wait_for_successful_transaction_receipt
from web3 import HTTPProvider, Web3
from web3.contract import Contract
from web3.middleware import construct_sign_and_send_raw_middleware

PARITY_DEV_ACCOUNT = "0x00a329c0648769A73afAc7F9381E08FB43dBEA72"
PARITY_DEV_KEY = "0x4D5DB4107D237DF6A3D58EE5F70AE63D73D7658D4026F2EEFD2F204C81682CB7"

HOME_RPC_URL = "http://localhost:8545"
FOREIGN_RPC_URL = "http://localhost:8645"

# How many blocks on the foreign chain must be mined for a transfer to be considered final by the bridge
REORG_DEPTH = 3

START_WEI_PER_ACCOUNT = 1 * 10 ** 18
BRIDGE_FUNDS = 1_000_000 * 10 ** 18


class TimeoutException(Exception):
    pass


class ServiceAlreadyStarted(Exception):
    pass


class Timer:
    def __init__(self, timeout):
        self.start_time = None
        self.timeout = timeout

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def start(self):
        self.start_time = time.time()

    def is_timed_out(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return self.time_passed > self.timeout

    @property
    def is_started(self):
        return self.start_time is not None

    @property
    def time_left(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return self.timeout - self.time_passed

    @property
    def time_passed(self):
        if self.start_time is None:
            raise ValueError("Timer is not started yet")
        return time.time() - self.start_time


def assert_within_timeout(check_function, timeout, poll_period=0.5):
    """
    Runs a check_function with assertions and give it some time to pass
    :param check_function: The function which will be periodically called. It should contain some assertions
    :param timeout: After this timeout non passing assertion will be raised
    :param poll_period: poll interval to check the check_function
    """
    with Timer(timeout) as timer:
        while True:
            try:
                check_function()
            except AssertionError as e:
                if not timer.is_timed_out():
                    time.sleep(min(poll_period, timer.time_left))
                else:
                    raise TimeoutException(
                        f"Assertion did not pass after {timeout} seconds. See causing exception for more details."
                    ) from e
            else:
                break


def assert_after_timout(check_function, timeout):
    time.sleep(timeout)
    check_function()


class Service:
    def __init__(
        self,
        args,
        *,
        name=None,
        env=None,
        timeout=5,
        poll_interval=0.2,
        process_settings=None,
    ):
        self.args = args
        self.name = name
        self.env = env
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.process = None
        self._process_settings = process_settings

        if self._process_settings is None:
            self._process_settings = {}

    def start(self):
        """Starts the service and wait for it to be up """
        if self.process:
            raise ServiceAlreadyStarted
        self.process = Popen(self.args, env=self.env, **self._process_settings)
        try:
            self._wait_for_up()
            return self.process
        except TimeoutException:
            self.terminate()
            raise

    def is_up(self):
        """Determine if the service is up"""
        return True

    def _wait_for_up(self):
        with Timer(self.timeout) as timer:
            while True:
                is_up = self.is_up()

                if not is_up:
                    if timer.is_timed_out():
                        raise TimeoutException(
                            f"Service {self.name} did not report to be up after {self.timeout} seconds"
                        )
                    else:
                        time.sleep(min(self.poll_interval, timer.time_left))
                else:
                    break

    def terminate(self):
        if self.process is None:
            return
        try:
            self.process.terminate()
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            warnings.warn(f"{self.name} did not terminate in time and had to be killed")
            self.process.kill()
            self.process.wait(timeout=5)
        self.process = None


class Node(Service):
    def __init__(self, path, *, name=None, port_shift=0):

        super().__init__(
            [
                "parity",
                # If we don't pass the --jsonrpc-server-threads
                # argument, the tests do fail on circle ci, because
                # transactions will not be mined.
                "--jsonrpc-server-threads",
                "8",
                "-d",
                str(path),
                "--config",
                "dev-insecure",
                "--ports-shift",
                f"{port_shift}",
            ],
            name=name,
        )
        self.web3 = Web3(HTTPProvider(f"http://localhost:{8545+port_shift}"))

    def is_up(self):
        try:
            version = self.web3.clientVersion
            return bool(version)
        except requests.exceptions.ConnectionError:
            return False


class Bridge(Service):

    HOST = "localhost"
    BASE_PORT = 8640

    def __init__(
        self,
        *,
        name=None,
        validator_private_key,
        token_contract_address,
        foreign_bridge_contract_address,
        home_bridge_contract_address,
        path,
        port_shift=0,
    ):
        self.port_shift = port_shift
        config = {
            "foreign_chain": {
                "rpc_url": FOREIGN_RPC_URL,
                "rpc_timeout": 5,
                "max_reorg_depth": REORG_DEPTH,
                "event_poll_interval": 0.5,
                "event_fetch_start_block_number": 0,
                "bridge_contract_address": str(foreign_bridge_contract_address),
                "token_contract_address": str(token_contract_address),
            },
            "home_chain": {
                "rpc_url": HOME_RPC_URL,
                "rpc_timeout": 5,
                "max_reorg_depth": 0,
                "event_poll_interval": 0.5,
                "event_fetch_start_block_number": 0,
                "bridge_contract_address": str(home_bridge_contract_address),
                "gas_price": 10_000_000_000,
                "minimum_validator_balance": 40_000_000_000_000_000,
                "balance_warn_poll_interval": 60.0,
            },
            "validator_private_key": {"raw": validator_private_key.to_hex()},
            "webservice": {
                "enabled": True,
                "host": self.HOST,
                "port": self.BASE_PORT + self.port_shift,
            },
        }
        with open(path, "w+") as f:
            toml.dump(config, f)
        super().__init__(["tlbc-bridge", "-c", path], name=name)

    def is_up(self):
        internal_state_url = (
            f"http://{self.HOST}:{self.BASE_PORT+self.port_shift}/bridge/internal-state"
        )
        try:
            requests.get(internal_state_url).json()
            # TODO check that bridge is ready
            print(f"{internal_state_url} is now up.")
            return True
        except requests.exceptions.ConnectionError:
            print(f"{internal_state_url} is not up yet.")
            return False


def mine_min_blocks(web3, number_of_blocks):
    """
    Mines a minimum of `number_of_blocks` blocks.

    Works by sending out transactions, assumes the parity InstaSeal engine
    """

    block_height = web3.eth.blockNumber
    while web3.eth.blockNumber < block_height + number_of_blocks:
        wait_for_successful_transaction_receipt(
            web3, web3.eth.sendTransaction({"from": PARITY_DEV_ACCOUNT})
        )


@pytest.fixture()
def accounts(accounts):
    return [PARITY_DEV_ACCOUNT] + list(accounts)


@pytest.fixture(scope="session")
def account_keys(account_keys):
    return [PARITY_DEV_KEY] + list(account_keys)


@pytest.fixture()
def node_home(tmp_path_factory):
    service = Node(
        name="home-node",
        port_shift=0,
        path=tmp_path_factory.mktemp("node", numbered=True),
    )
    service.start()
    yield service
    service.terminate()


@pytest.fixture()
def node_foreign(tmp_path_factory):
    service = Node(
        name="foreign-node",
        port_shift=100,
        path=tmp_path_factory.mktemp("node", numbered=True),
    )
    service.start()
    yield service
    service.terminate()


@pytest.fixture()
def web3_home(node_home, accounts, account_keys):
    web3 = Web3(HTTPProvider(HOME_RPC_URL))
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account_keys))
    for account in accounts[1:]:
        wait_for_successful_transaction_receipt(
            web3,
            web3.eth.sendTransaction(
                {"from": accounts[0], "to": account, "value": START_WEI_PER_ACCOUNT}
            ),
        )
    return web3


@pytest.fixture()
def web3_foreign(node_foreign, accounts, account_keys):
    web3 = Web3(HTTPProvider(FOREIGN_RPC_URL))
    web3.middleware_onion.add(construct_sign_and_send_raw_middleware(account_keys))
    for account in accounts[1:]:
        wait_for_successful_transaction_receipt(
            web3,
            web3.eth.sendTransaction(
                {"from": accounts[0], "to": account, "value": START_WEI_PER_ACCOUNT}
            ),
        )
    return web3


@pytest.fixture()
def deploy_contract_on_chain(contract_assets, account_keys):
    """A function that deploys a contract on a chain specified via a web3 instance."""

    def deploy(
        web3: Web3, contract_identifier: str, *, constructor_args=()
    ) -> Contract:
        return deploy_compiled_contract(
            abi=contract_assets[contract_identifier]["abi"],
            bytecode=contract_assets[contract_identifier]["bytecode"],
            web3=web3,
            constructor_args=constructor_args,
            private_key=account_keys[0],
        )

    return deploy


@pytest.fixture()
def token_contract(deploy_contract_on_chain, web3_foreign, accounts):
    """The token contract on the foreign chain."""
    constructor_args = (
        "Trustlines Network Token",
        "TLN",
        18,
        accounts[0],
        BRIDGE_FUNDS,
    )

    token_contract = deploy_contract_on_chain(
        web3_foreign, "TrustlinesNetworkToken", constructor_args=constructor_args
    )

    assert token_contract.functions.balanceOf(accounts[0]).call() > 0

    for account in accounts[1:]:
        wait_for_successful_transaction_receipt(
            web3_foreign,
            token_contract.functions.transfer(account, 10 ** 18).transact(
                {"from": accounts[0]}
            ),
        )

    return token_contract


@pytest.fixture()
def foreign_bridge_contract(deploy_contract_on_chain, web3_foreign, token_contract):
    """The foreign bridge contract."""
    return deploy_contract_on_chain(
        web3_foreign, "ForeignBridge", constructor_args=(token_contract.address,)
    )


@pytest.fixture()
def validators(accounts):
    return accounts[7:10]


@pytest.fixture()
def validator_keys(account_keys):
    return account_keys[7:10]


@pytest.fixture()
def bridge_addresses(validators):
    return validators


@pytest.fixture()
def system_address(accounts):
    """Address pretending to be the system address."""
    return accounts[0]


@pytest.fixture()
def validator_proxy_contract(deploy_contract_on_chain, web3_home, system_address):
    """The plain validator proxy contract."""
    contract = deploy_contract_on_chain(
        web3_home, "TestValidatorProxy", constructor_args=([], system_address)
    )

    assert contract.functions.systemAddress().call() == system_address

    return contract


@pytest.fixture()
def validator_proxy_with_validators(
    validator_proxy_contract, system_address, validators
):
    """Validator proxy contract using the proxy validators."""
    validator_proxy_contract.functions.updateValidators(validators).transact(
        {"from": system_address}
    )
    return validator_proxy_contract


@pytest.fixture()
def home_bridge_contract(
    deploy_contract_on_chain, validator_proxy_with_validators, web3_home, accounts
):
    """The home bridge contract."""
    contract = deploy_contract_on_chain(
        web3_home,
        "HomeBridge",
        constructor_args=(validator_proxy_with_validators.address, 50),
    )

    wait_for_successful_transaction_receipt(
        web3_home,
        contract.functions.fund().transact(
            {"from": accounts[0], "gas": 100_000, "value": BRIDGE_FUNDS}
        ),
    )

    assert web3_home.eth.getBalance(contract.address) == BRIDGE_FUNDS

    return contract


@pytest.fixture()
def bridges(
    validator_keys,
    token_contract,
    home_bridge_contract,
    foreign_bridge_contract,
    tmp_path_factory,
):
    bridges = []
    for i, key in enumerate(validator_keys):
        bridge = Bridge(
            validator_private_key=key,
            token_contract_address=token_contract.address,
            foreign_bridge_contract_address=foreign_bridge_contract.address,
            home_bridge_contract_address=home_bridge_contract.address,
            path=tmp_path_factory.mktemp("bridge", numbered=True) / "config.toml",
            name=f"Bridge {i}",
            port_shift=i,
        )
        bridges.append(bridge)

    yield bridges

    for bridge in bridges:
        bridge.terminate()


@pytest.fixture()
def started_bridges(bridges):
    for bridge in bridges:
        bridge.start()

    yield bridges

    for bridge in bridges:
        bridge.terminate()


def test_simple_transfer(
    web3_home,
    web3_foreign,
    foreign_bridge_contract,
    token_contract,
    accounts,
    started_bridges,
):
    """
    Tests whether a simple transfer with all bridges online works
    """
    sender = accounts[3]
    value = 5000
    foreign_balance_before = token_contract.functions.balanceOf(sender).call()
    home_balance_before = web3_home.eth.getBalance(sender)

    wait_for_successful_transaction_receipt(
        web3_foreign,
        token_contract.functions.transfer(
            foreign_bridge_contract.address, value
        ).transact({"from": sender}),
    )

    mine_min_blocks(web3_foreign, REORG_DEPTH)

    def check_balance():
        foreign_balance_after = token_contract.functions.balanceOf(sender).call()
        home_balance_after = web3_home.eth.getBalance(sender)

        assert foreign_balance_before - foreign_balance_after == value
        assert home_balance_before - home_balance_after == -value

    assert_within_timeout(check_balance, 10)


def test_offline_validators_validates_not_complete_transfer(
    web3_home, web3_foreign, foreign_bridge_contract, token_contract, accounts, bridges
):
    """
    Tests whether a transfer initiated when threshold validators are offline will be effective when enough validators turn online
    """
    bridges[0].start()

    sender = accounts[3]
    value = 5000
    foreign_balance_before = token_contract.functions.balanceOf(sender).call()
    home_balance_before = web3_home.eth.getBalance(sender)

    wait_for_successful_transaction_receipt(
        web3_foreign,
        token_contract.functions.transfer(
            foreign_bridge_contract.address, value
        ).transact({"from": sender}),
    )

    mine_min_blocks(web3_foreign, REORG_DEPTH)

    def check_balances_bridge_transfer_not_complete():
        foreign_balance_transfer_not_complete = token_contract.functions.balanceOf(
            sender
        ).call()
        home_balance_transfer_not_complete = web3_home.eth.getBalance(sender)

        assert foreign_balance_before - foreign_balance_transfer_not_complete == value
        assert home_balance_before == home_balance_transfer_not_complete

    assert_after_timout(check_balances_bridge_transfer_not_complete, 10)

    bridges[1].start()

    def check_balance_transfer_complete():
        home_balance_transfer_complete = web3_home.eth.getBalance(sender)

        assert home_balance_transfer_complete - home_balance_before == value

    assert_within_timeout(check_balance_transfer_complete, 10)


def test_offline_validators_do_not_validates_complete_transfer(
    web3_home,
    web3_foreign,
    foreign_bridge_contract,
    token_contract,
    accounts,
    bridges,
    validators,
):
    """
    Tests that a transfer initiated when threshold validators are online will not be pointlessly validated when different validator turn online
    """
    bridge_2_address = validators[2]
    before_tx_count = web3_home.eth.getTransactionCount(bridge_2_address)

    bridges[0].start()
    bridges[1].start()

    sender = accounts[3]
    value = 5000
    home_balance_before = web3_home.eth.getBalance(sender)

    wait_for_successful_transaction_receipt(
        web3_foreign,
        token_contract.functions.transfer(
            foreign_bridge_contract.address, value
        ).transact({"from": sender}),
    )

    mine_min_blocks(web3_foreign, REORG_DEPTH)

    def check_balance_transfer_complete():
        home_balance_transfer_complete = web3_home.eth.getBalance(sender)
        assert home_balance_transfer_complete - home_balance_before == value

    # We need to wait for the transaction to be completed before starting bridges[2]
    assert_within_timeout(check_balance_transfer_complete, 10)

    bridges[2].start()

    def check_no_transaction_sent():
        after_tx_count = web3_home.eth.getTransactionCount(bridge_2_address)

        assert after_tx_count == before_tx_count

    assert_after_timout(check_no_transaction_sent, 10)


def test_parity_node_restarting(
    web3_home,
    web3_foreign,
    foreign_bridge_contract,
    token_contract,
    accounts,
    bridges,
    node_home,
    node_foreign,
):
    """
    Tests that the parity node bound to the bridge can crash and restart without impacting the bridge
    """
    bridges[0].start()
    bridges[1].start()

    node_home.terminate()
    node_foreign.terminate()

    assert bridges[0].is_up()

    node_home.start()
    node_foreign.start()

    sender = accounts[3]
    value = 5000
    home_balance_before = web3_home.eth.getBalance(sender)

    wait_for_successful_transaction_receipt(
        web3_foreign,
        token_contract.functions.transfer(
            foreign_bridge_contract.address, value
        ).transact({"from": sender}),
    )

    mine_min_blocks(web3_foreign, REORG_DEPTH)

    def check_balance_transfer_complete():
        home_balance_transfer_complete = web3_home.eth.getBalance(sender)
        assert home_balance_transfer_complete - home_balance_before == value

    assert_within_timeout(check_balance_transfer_complete, 10)


def test_validator_set_changes_transfer(
    web3_home,
    web3_foreign,
    foreign_bridge_contract,
    token_contract,
    accounts,
    bridges,
    bridge_addresses,
    validator_proxy_contract,
    system_address,
):
    """
    Tests that a transfer initiated when not enough validators are online to confirm it will be confirmed
    when the validator set changes to have enough validators online
    """

    inactive_address = accounts[2]
    assert inactive_address not in bridge_addresses
    initial_validators = [bridge_addresses[0], inactive_address, bridge_addresses[2]]
    validator_proxy_contract.functions.updateValidators(initial_validators).transact(
        {"from": system_address}
    )

    # Only bridges[0] and bridges[2] are validators, so bridge transfers will not be complete with
    # only bridges[0] and bridges[1] online
    bridges[0].start()
    bridges[1].start()

    sender = accounts[3]
    value = 5000
    home_balance_before = web3_home.eth.getBalance(sender)

    wait_for_successful_transaction_receipt(
        web3_foreign,
        token_contract.functions.transfer(
            foreign_bridge_contract.address, value
        ).transact({"from": sender}),
    )

    mine_min_blocks(web3_foreign, REORG_DEPTH)

    # new validators include two online bridges: bridges[0] and bridges[1] and bridge transfers should be complete
    validator_proxy_contract.functions.updateValidators(bridge_addresses).transact(
        {"from": system_address}
    )

    def check_balance_transfer_complete():
        home_balance_transfer_complete = web3_home.eth.getBalance(sender)
        assert home_balance_transfer_complete - home_balance_before == value

    assert_within_timeout(check_balance_transfer_complete, 10)
