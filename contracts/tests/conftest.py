from collections import namedtuple

import eth_tester
import pytest
from data_generation import make_block_header
from deploy_tools.deploy import wait_for_successful_transaction_receipt
from deploy_util import (
    initialize_deposit_locker,
    initialize_test_validator_slasher,
    initialize_validator_set,
)

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6

RELEASE_TIMESTAMP_OFFSET = 3600 * 24 * 180

# Fix the indexes used to get addresses from the test chain.
# Mind the difference between count and index.
HONEST_VALIDATOR_COUNT = 2
MALICIOUS_VALIDATOR_INDEX, MALICIOUS_NON_VALIDATOR_INDEX = range(
    HONEST_VALIDATOR_COUNT, HONEST_VALIDATOR_COUNT + 2
)

AUCTION_DURATION_IN_DAYS = 14
AUCTION_START_PRICE = 10000 * 10 ** 18

SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")


@pytest.fixture(scope="session")
def release_timestamp(web3):
    """release timestamp used for DepositLocker contract"""
    now = web3.eth.getBlock("latest").timestamp
    return now + RELEASE_TIMESTAMP_OFFSET


@pytest.fixture(scope="session")
def deposit_locker_init(release_timestamp, web3):
    def init(deposit_locker, depositors_proxy):
        txid = deposit_locker.functions.init(
            _releaseTimestamp=release_timestamp,
            _slasher="0x0000000000000000000000000000000000000000",
            _depositorsProxy=depositors_proxy,
        ).transact()
        wait_for_successful_transaction_receipt(web3, txid)

    return init


@pytest.fixture(scope="session")
def deposit_amount():
    return 100


@pytest.fixture(scope="session")
def maximal_number_of_auction_participants():
    number_of_participants = 123
    return number_of_participants


@pytest.fixture(scope="session")
def minimal_number_of_auction_participants():
    return 50


@pytest.fixture(scope="session")
def fake_auction_address(accounts):
    return accounts[4]


@pytest.fixture(scope="session")
def malicious_non_validator_address(accounts):
    return accounts[MALICIOUS_NON_VALIDATOR_INDEX]


@pytest.fixture()
def malicious_non_validator_key(account_keys):
    return account_keys[MALICIOUS_NON_VALIDATOR_INDEX]


@pytest.fixture(scope="session")
def malicious_validator_address(accounts):
    return accounts[MALICIOUS_VALIDATOR_INDEX]


@pytest.fixture()
def malicious_validator_key(account_keys):
    return account_keys[MALICIOUS_VALIDATOR_INDEX]


@pytest.fixture(scope="session")
def validators(accounts, malicious_validator_address):
    return accounts[:HONEST_VALIDATOR_COUNT] + [malicious_validator_address]


@pytest.fixture(scope="session")
def validator_set_contract_session(
    deploy_contract, validator_proxy_contract, validators, system_address, web3
):
    deployed_test_validator_set = deploy_contract(
        "TestValidatorSet", constructor_args=(system_address,)
    )
    initialized_test_validator_set = initialize_validator_set(
        deployed_test_validator_set,
        validators,
        validator_proxy_contract.address,
        web3=web3,
    )

    return initialized_test_validator_set


@pytest.fixture(scope="session")
def equivocation_inspector_contract_session(deploy_contract):
    return deploy_contract("TestEquivocationInspector")


@pytest.fixture(scope="session")
def non_initialized_validator_slasher_contract_session(deploy_contract):
    return deploy_contract("ValidatorSlasher")


@pytest.fixture(scope="session")
def non_initialized_deposit_locker_contract_session(deploy_contract):
    return deploy_contract("DepositLocker")


@pytest.fixture(scope="session")
def initialized_deposit_and_slasher_contracts(
    validators, deploy_contract, fake_auction_address, web3, release_timestamp
):
    slasher_contract = deploy_contract("ValidatorSlasher")
    locker_contract = deploy_contract("DepositLocker")
    """Initializes both the slasher and deposit contract, both initialisation are in the same fixture because we want
    a snapshot where both contracts are initialized and aware of the address of the other"""

    slasher_contract_address = slasher_contract.address
    auction_contract_address = fake_auction_address
    initialized_deposit_contract = initialize_deposit_locker(
        locker_contract,
        release_timestamp,
        slasher_contract_address,
        auction_contract_address,
        web3,
    )

    # initialize slasher contract
    fund_contract_address = initialized_deposit_contract.address

    initialized_slasher_contract = initialize_test_validator_slasher(
        slasher_contract, fund_contract_address, web3
    )

    Deposit_slasher_contracts = namedtuple(
        "Deposit_slasher_contracts", "deposit_contract, slasher_contract"
    )
    return Deposit_slasher_contracts(
        deposit_contract=initialized_deposit_contract,
        slasher_contract=initialized_slasher_contract,
    )


@pytest.fixture
def validator_slasher_contract(initialized_deposit_and_slasher_contracts):

    return initialized_deposit_and_slasher_contracts.slasher_contract


@pytest.fixture
def deposit_locker_contract(initialized_deposit_and_slasher_contracts):

    return initialized_deposit_and_slasher_contracts.deposit_contract


@pytest.fixture
def deposit_locker_contract_with_deposits(
    chain_cleanup,
    initialized_deposit_and_slasher_contracts,
    validators,
    malicious_validator_address,
    deposit_amount,
    fake_auction_address,
):

    deposit_contract = initialized_deposit_and_slasher_contracts.deposit_contract

    for validator in validators:
        deposit_contract.functions.registerDepositor(validator).transact(
            {"from": fake_auction_address}
        )

    deposit_contract.functions.deposit(deposit_amount).transact(
        {"from": fake_auction_address, "value": deposit_amount * len(validators)}
    )

    return deposit_contract


@pytest.fixture()
def block_header_by_malicious_validator(malicious_validator_key):
    return make_block_header(private_key=malicious_validator_key)


@pytest.fixture()
def block_header_by_malicious_non_validator(malicious_non_validator_key):
    return make_block_header(private_key=malicious_non_validator_key)


@pytest.fixture(scope="session")
def validator_auction_contract(deploy_contract, whitelist, web3, deposit_locker_init):
    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker_init(deposit_locker, contract.address)

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    return contract


@pytest.fixture(scope="session")
def real_price_validator_auction_contract(
    deploy_contract,
    whitelist,
    maximal_number_of_auction_participants,
    minimal_number_of_auction_participants,
    web3,
    deposit_locker_init,
):
    deposit_locker = deploy_contract("DepositLocker")

    contract = deploy_contract(
        "ValidatorAuction",
        constructor_args=(
            AUCTION_START_PRICE,
            AUCTION_DURATION_IN_DAYS,
            minimal_number_of_auction_participants,
            maximal_number_of_auction_participants,
            deposit_locker.address,
        ),
    )
    deposit_locker_init(deposit_locker, contract.address)

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    return contract


@pytest.fixture(scope="session")
def no_whitelist_validator_auction_contract(deploy_contract, web3, deposit_locker_init):
    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker_init(deposit_locker, contract.address)

    return contract


@pytest.fixture(scope="session")
def almost_filled_validator_auction(
    deploy_contract,
    whitelist,
    maximal_number_of_auction_participants,
    web3,
    deposit_locker_init,
):
    """Validator auction contract missing one bid to reach the maximum amount of bidders
    account[1] has not bid and can be used to test the behaviour of sending the last bid"""

    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker_init(deposit_locker, contract.address)

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    contract.functions.startAuction().transact()

    for participant in whitelist[1:maximal_number_of_auction_participants]:
        contract.functions.bid().transact({"from": participant, "value": 100})

    return contract


@pytest.fixture(scope="session")
def whitelist(chain, maximal_number_of_auction_participants):
    """whitelisted well-funded accounts, accounts[0] is not in the whitelist"""
    # some other tests do also call add_account and we do not want to
    # include them (it just takes longer)
    whitelist = list(chain.get_accounts()[1:10]) + [
        chain.add_account(f"0x{i:064}")
        for i in range(100, 100 + maximal_number_of_auction_participants)
    ]

    send_ether_to_whitelisted_accounts(chain, whitelist)

    return whitelist


def send_ether_to_whitelisted_accounts(chain, whitelist):
    account_0 = chain.get_accounts()[0]

    for participant in whitelist:
        chain.send_transaction(
            {"from": account_0, "to": participant, "gas": 21000, "value": 10_000_000}
        )


def add_whitelist_to_validator_auction_contract(contract, whitelist):
    contract.functions.addToWhitelist(whitelist).transact()
    return contract


@pytest.fixture()
def block_reward_amount(chain, web3):
    mining_reward_address = "0x0000000000000000000000000000000000000000"
    balance_before = web3.eth.getBalance(mining_reward_address)
    chain.mine_block()
    balance_after = web3.eth.getBalance(mining_reward_address)
    return balance_after - balance_before


@pytest.fixture(scope="session")
def tln_token_contract(deploy_contract, premint_token_address, premint_token_value):
    token_name = "Trustlines Network Token"
    token_symbol = "TLN"
    token_decimal = 18
    constructor_args = (
        token_name,
        token_symbol,
        token_decimal,
        premint_token_address,
        premint_token_value,
    )

    return deploy_contract("TrustlinesNetworkToken", constructor_args=constructor_args)


@pytest.fixture(scope="session")
def premint_token_address(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def premint_token_value():
    return 132_456


@pytest.fixture(scope="session")
def validator_proxy_contract(deploy_contract, web3, system_address, accounts):
    contract = deploy_contract(
        "TestValidatorProxy", constructor_args=([], system_address)
    )

    assert contract.functions.systemAddress().call() == system_address

    return contract


@pytest.fixture()
def validator_proxy_with_validators(
    validator_proxy_contract, system_address, proxy_validators
):
    validator_proxy_contract.functions.updateValidators(proxy_validators).transact(
        {"from": system_address}
    )
    return validator_proxy_contract


@pytest.fixture()
def foreign_bridge_contract(deploy_contract, tln_token_contract):
    return deploy_contract(
        "ForeignBridge", constructor_args=(tln_token_contract.address,)
    )


@pytest.fixture()
def proxy_validators(accounts):
    return accounts[:5]


@pytest.fixture(scope="session")
def system_address(accounts):
    return accounts[0]


@pytest.fixture()
def home_bridge_contract(deploy_contract, validator_proxy_with_validators, chain):
    """ deploy a HomeBridge contract connected to the
    validator_proxy_with_validators contract"""

    contract = deploy_contract(
        "HomeBridge", constructor_args=(validator_proxy_with_validators.address, 50)
    )

    account_0 = chain.get_accounts()[0]

    contract.functions.fund().transact(
        {"from": account_0, "to": contract.address, "gas": 100_000, "value": 1_000_000}
    )

    return contract
