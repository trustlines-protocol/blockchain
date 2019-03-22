import pytest

from collections import namedtuple

from .deploy_util import (
    initialize_validator_set,
    initialize_test_validator_slasher,
    initialize_deposit_locker,
)

from .data_generation import make_equivocated_signed_block_header


RELEASE_BLOCK_NUMBER_OFFSET = 50

# Fix the indexes used to get addresses from the test chain.
# Mind the difference between count and index.
HONEST_VALIDATOR_COUNT = 2
MALICIOUS_VALIDATOR_INDEX = HONEST_VALIDATOR_COUNT
MALICIOUS_NON_VALIDATOR_INDEX = MALICIOUS_VALIDATOR_INDEX + 1


SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")


@pytest.fixture(scope="session")
def deposit_amount():
    return 100


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
def initialised_deposit_and_slasher_contracts(validators, deploy_contract, web3):
    slasher_contract = deploy_contract("TestValidatorSlasher")
    locker_contract = deploy_contract("DepositLocker")

    """Initialises both the slasher and deposit contract, both initialisation are in the same fixture because we want
    a snapshot where both contracts are initialised and aware of the address of the other"""

    # initialise the deposit contract
    release_number = web3.eth.blockNumber + RELEASE_BLOCK_NUMBER_OFFSET

    # we want to test withdrawing before reaching block_number
    # if we reach this block number via deploying and initialising contracts, we will need to increase this number
    # if this number is too high, tests are slowed down

    slasher_contract_address = slasher_contract.address

    initialised_deposit_contract = initialize_deposit_locker(
        locker_contract, release_number, slasher_contract_address, web3
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
):

    deposit_contract = initialised_deposit_and_slasher_contracts.deposit_contract

    for validator in validators:
        deposit_contract.functions.deposit(validator).transact(
            {"from": validator, "value": deposit_amount}
        )

    return deposit_contract


@pytest.fixture()
def equivocated_signed_block_header_malicious_validator(malicious_validator_key):
    return make_equivocated_signed_block_header(private_key=malicious_validator_key)


@pytest.fixture()
def equivocated_signed_block_header_incorrect_structure(malicious_validator_key):
    return make_equivocated_signed_block_header(
        private_key=malicious_validator_key, use_incorrect_structure=True
    )


@pytest.fixture()
def equivocated_signed_block_header_short_list(malicious_validator_key):
    return make_equivocated_signed_block_header(
        private_key=malicious_validator_key, use_short_list=True
    )


@pytest.fixture()
def equivocated_signed_block_header_malicious_non_validator(
    malicious_non_validator_key
):
    return make_equivocated_signed_block_header(private_key=malicious_non_validator_key)
