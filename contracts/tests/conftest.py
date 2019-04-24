from collections import namedtuple

import pytest
import eth_tester

from .deploy_util import (
    initialize_validator_set,
    initialize_test_validator_slasher,
    initialize_deposit_locker,
)

from .data_generation import make_block_header

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6


RELEASE_BLOCK_NUMBER_OFFSET = 50

# Fix the indexes used to get addresses from the test chain.
# Mind the difference between count and index.
HONEST_VALIDATOR_COUNT = 2
MALICIOUS_VALIDATOR_INDEX = HONEST_VALIDATOR_COUNT
MALICIOUS_NON_VALIDATOR_INDEX = MALICIOUS_VALIDATOR_INDEX + 1

AUCTION_DURATION_IN_DAYS = 14
AUCTION_START_PRICE = 10000 * 10 ** 18

SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")


@pytest.fixture(scope="session")
def deposit_amount():
    return 100


@pytest.fixture(scope="session")
def number_of_auction_participants():
    number_of_participants = 123
    return number_of_participants


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
def validator_set_contract_session(deploy_contract, validators, web3):
    deployed_test_validator_set = deploy_contract("TestValidatorSet")
    initialized_test_validator_set = initialize_validator_set(
        deployed_test_validator_set, validators, web3=web3
    )

    return initialized_test_validator_set


@pytest.fixture(scope="session")
def equivocation_inspector_contract_session(deploy_contract):
    return deploy_contract("TestEquivocationInspector")


@pytest.fixture(scope="session")
def non_initialised_validator_slasher_contract_session(deploy_contract):
    return deploy_contract("ValidatorSlasher")


@pytest.fixture(scope="session")
def non_initialised_deposit_locker_contract_session(deploy_contract):
    return deploy_contract("DepositLocker")


@pytest.fixture(scope="session")
def initialised_deposit_and_slasher_contracts(
    validators, deploy_contract, fake_auction_address, web3
):
    slasher_contract = deploy_contract("ValidatorSlasher")
    locker_contract = deploy_contract("DepositLocker")
    """Initialises both the slasher and deposit contract, both initialisation are in the same fixture because we want
    a snapshot where both contracts are initialised and aware of the address of the other"""

    # initialise the deposit contract
    release_number = web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET

    # we want to test withdrawing before reaching block_number
    # if we reach this block number via deploying and initialising contracts, we will need to increase this number
    # if this number is too high, tests are slowed down

    slasher_contract_address = slasher_contract.address
    auction_contract_address = fake_auction_address
    initialised_deposit_contract = initialize_deposit_locker(
        locker_contract,
        release_number,
        slasher_contract_address,
        auction_contract_address,
        web3,
    )

    # initialise slasher contract
    fund_contract_address = initialised_deposit_contract.address

    initialised_slasher_contract = initialize_test_validator_slasher(
        slasher_contract, validators, fund_contract_address, web3
    )

    Deposit_slasher_contracts = namedtuple(
        "Deposit_slasher_contracts", "deposit_contract, slasher_contract"
    )
    return Deposit_slasher_contracts(
        deposit_contract=initialised_deposit_contract,
        slasher_contract=initialised_slasher_contract,
    )


@pytest.fixture
def validator_slasher_contract(initialised_deposit_and_slasher_contracts):

    return initialised_deposit_and_slasher_contracts.slasher_contract


@pytest.fixture
def deposit_locker_contract(initialised_deposit_and_slasher_contracts):

    return initialised_deposit_and_slasher_contracts.deposit_contract


@pytest.fixture
def deposit_locker_contract_with_deposits(
    chain_cleanup,
    initialised_deposit_and_slasher_contracts,
    validators,
    malicious_validator_address,
    deposit_amount,
    fake_auction_address,
):

    deposit_contract = initialised_deposit_and_slasher_contracts.deposit_contract

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
def validator_auction_contract(deploy_contract, whitelist, web3):
    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker.functions.init(
        _releaseBlockNumber=web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET,
        _slasher="0x0000000000000000000000000000000000000000",
        _depositorsProxy=contract.address,
    ).transact()

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    return contract


@pytest.fixture(scope="session")
def real_price_validator_auction_contract(
    deploy_contract, whitelist, number_of_auction_participants, web3
):
    deposit_locker = deploy_contract("DepositLocker")

    contract = deploy_contract(
        "ValidatorAuction",
        constructor_args=(
            AUCTION_START_PRICE,
            AUCTION_DURATION_IN_DAYS,
            number_of_auction_participants,
            deposit_locker.address,
        ),
    )
    deposit_locker.functions.init(
        _releaseBlockNumber=web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET,
        _slasher="0x0000000000000000000000000000000000000000",
        _depositorsProxy=contract.address,
    ).transact()

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    return contract


@pytest.fixture(scope="session")
def no_whitelist_validator_auction_contract(deploy_contract, web3):
    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker.functions.init(
        _releaseBlockNumber=web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET,
        _slasher="0x0000000000000000000000000000000000000000",
        _depositorsProxy=contract.address,
    ).transact()

    return contract


@pytest.fixture(scope="session")
def almost_filled_validator_auction(
    deploy_contract, whitelist, number_of_auction_participants, web3
):
    """Validator auction contract missing one bid to reach the maximum amount of bidders
    account[1] has not bid and can be used to test the behaviour of sending the last bid"""

    deposit_locker = deploy_contract("DepositLocker")
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice", constructor_args=(deposit_locker.address,)
    )
    deposit_locker.functions.init(
        _releaseBlockNumber=web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET,
        _slasher="0x0000000000000000000000000000000000000000",
        _depositorsProxy=contract.address,
    ).transact()

    add_whitelist_to_validator_auction_contract(contract, whitelist)

    contract.functions.startAuction().transact()

    for participant in whitelist[1:number_of_auction_participants]:
        contract.functions.bid().transact({"from": participant, "value": 100})

    return contract


@pytest.fixture(scope="session")
def whitelist(chain, number_of_auction_participants):
    """Every known accounts appart from accounts[0] is in the whitelist"""
    new_chain = chain
    for i in range(100, 100 + number_of_auction_participants):
        new_chain.add_account(
            "0x0000000000000000000000000000000000000000000000000000000000000" + str(i)
        )

    whitelist = new_chain.get_accounts()[1:]

    send_ether_to_whitelisted_accounts(chain, whitelist)

    return whitelist


def send_ether_to_whitelisted_accounts(chain, whitelist):
    account_0 = chain.get_accounts()[0]

    for participant in whitelist:
        chain.send_transaction(
            {"from": account_0, "to": participant, "gas": 21000, "value": 10000000}
        )


def add_whitelist_to_validator_auction_contract(contract, whitelist):
    contract.functions.addToWhitelist(whitelist).transact()
    return contract
