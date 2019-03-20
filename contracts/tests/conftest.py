import pytest
import rlp
import codecs
from collections import namedtuple

from .deploy_util import (
    initialize_validator_set,
    initialize_test_validator_slasher,
    initialize_deposit_locker,
)


RELEASE_BLOCK_NUMBER_OFFSET = 50

# Fix the indexes used to get addresses from the test chain.
# Mind the difference between count and index.
HONEST_VALIDATOR_COUNT = 2
MALICIOUS_VALIDATOR_INDEX = HONEST_VALIDATOR_COUNT
MALICIOUS_NON_VALIDATOR_INDEX = MALICIOUS_VALIDATOR_INDEX + 1

# Duration and time values are defined in seconds.
STEP = 10
STEP_DURATION = 5
STEP_TIME_BEGIN = STEP * STEP_DURATION
STEP_TIME_END = STEP_TIME_BEGIN + STEP_DURATION - 1

# Maximum uint256 value in Solidity for the timestamp field boundaries.
MAX_UINT = 2 ** 256 - 1


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


@pytest.fixture(scope="session")
def signed_block_header_one():
    unsigned_block_header = codecs.decode(
        "f901fca03656d92a2bbe7712b265bde6f08a2c86fb90e1342d61fb568b8603060e9f1279a01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d4934794c8fce36cced702809203c9121ee6767a376786cca0f2458903b778efe98366ace17478352f2d8621309b6f9122708b321d040fdc24a056e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421a056e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421b901000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000090fffffffffffffffffffffffffffffffd83032da7837a120080845c093dd09fde830201068f5061726974792d457468657265756d86312e33302e31826c69",  # noqa: E501
        "hex",
    )

    signature = "334d0042f3d8ddded873382b4f811a9088e5fbf5ea8676c4f40084351712e0dc57c07beac05d698c432e2d30533bdf88c6b08b1fd65f98136a478b29ae132ad200"  # noqa: E501

    return SignedBlockHeader(unsigned_block_header, signature)


@pytest.fixture(scope="session")
def signed_block_header_two():
    unsigned_block_header = codecs.decode(
        "f901fca0447983e6c92edeb95e50b707066224fb638d892a19e2508a92b207b9669c0e0ba01dcc4de8dec75d7aab85b567b6ccd41ad312451b948a7413f0a142fd40d493479427e6925dd78fabcc9d95da178f9ebb986fa66fdba03040fdb397088fde2007ddce97540c4024a9d8dd9fcb3f580b5fd2495516c7f6a056e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421a056e81f171bcc55a6ff8345e692c0f86e5b48e01b996cadc001622fb5e363b421b901000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000090fffffffffffffffffffffffffffffffe83032da8837a120080845c093dd59fde830201068f5061726974792d457468657265756d86312e33302e31826c69",  # noqa: E501
        "hex",
    )

    signature = "092743f2d606e3ead3b3dc9d2d2248e9f9aae2997c6d71dfbb7fed39df0c86d9044a5f9a3a263e989c4af3b6b920d2b8c4c65e1df4a8717f314de0b864cd702700"  # noqa: E501

    return SignedBlockHeader(unsigned_block_header, signature)


@pytest.fixture
def signed_block_header_one_address(signed_block_header_one):
    block_header = rlp.decode(signed_block_header_one.unsignedBlockHeader)
    return block_header[2].hex()


@pytest.fixture(
    params=[STEP_TIME_BEGIN, STEP_TIME_BEGIN + 1, STEP_TIME_END - 1, STEP_TIME_END]
)
def timestamp_within_step_one(request):
    """Boundary timestamp values within a step, depending on the step duration.

    Note that the 'one' is not related to the step number (which is derived from the
    global variable), but to the block tuple index used for equivocation proofs.
    """
    return request.param


@pytest.fixture(
    params=[STEP_TIME_BEGIN, STEP_TIME_BEGIN + 1, STEP_TIME_END - 1, STEP_TIME_END]
)
def timestamp_within_step_two(request):
    """Duplicate of timestamp_within_step_one with purpose.

    The intention is to have two parametrized timestamp fixtures which can be
    use combined to test all combinations of them. Exporting them as standalone
    fixtures seems to be necessary, since fixtures can't be parametrized
    partially.
    Note that the 'two' is not related to the step number (which is derived from the
    global variable), but to the block tuple index used for equivocation proofs.
    """
    return request.param


@pytest.fixture(params=[1, STEP_TIME_BEGIN - 1, STEP_TIME_END + 1, MAX_UINT])
def timestamp_outside_step(request):
    """Boundary timestamp values outside a step, depending on the step duration."""
    return request.param


@pytest.fixture
def two_equivocating_block_header(
    signed_block_header_one,
    timestamp_within_step_one,
    signed_block_header_two,
    timestamp_within_step_two,
):

    """Test data of two equivocating block header.

    Both blocks fulfill all rules to get verified as equivocated.
    These block header can be signed by any address to use in further test cases.
    Note that this fixture is using the parametrized timestamp values.
    """

    block_header_one = rlp.decode(signed_block_header_one.unsignedBlockHeader)
    block_header_two = rlp.decode(signed_block_header_two.unsignedBlockHeader)

    block_header_one[11] = timestamp_within_step_one
    block_header_two[11] = timestamp_within_step_two

    rlp_block_header_one = rlp.encode(block_header_one)
    rlp_block_header_two = rlp.encode(block_header_two)

    return (rlp_block_header_one, rlp_block_header_two)


@pytest.fixture
def sign_two_equivocating_block_header(two_equivocating_block_header):

    """Function to sign two equivocating blocks with a given key.

    Both blocks fulfill all rules to get verified as equivocated.
    Both blocks will be signed by the address related to the provided private key.
    """

    def sign(private_key):
        rlp_block_header_one = two_equivocating_block_header[0]
        rlp_block_header_two = two_equivocating_block_header[1]

        signature_one = private_key.sign_msg(rlp_block_header_one).to_bytes()
        signature_two = private_key.sign_msg(rlp_block_header_two).to_bytes()

        return (
            SignedBlockHeader(rlp_block_header_one, signature_one),
            SignedBlockHeader(rlp_block_header_two, signature_two),
        )

    return sign


@pytest.fixture
def two_signed_blocks_no_list_header(
    two_equivocating_block_header, malicious_validator_key
):

    """Test data with two blocks which fulfill all equivocation rules, except one has a non list type header."""

    unsigned_block_header_one = rlp.encode(codecs.decode("123456789abcde", "hex"))
    rlp_unsigned_block_header_one = rlp.encode(unsigned_block_header_one)
    rlp_unsigned_block_header_two = two_equivocating_block_header[1]

    signature_one = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_one
    ).to_bytes()
    signature_two = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_two
    ).to_bytes()

    return (
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_one),
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_two),
    )


@pytest.fixture
def two_signed_blocks_too_short_header(
    two_equivocating_block_header, malicious_validator_key
):

    """Test data with two blocks which fulfill all equivocation rules, except one has a too short header."""

    unsigned_block_header_one = rlp.decode(two_equivocating_block_header[0])
    unsigned_block_header_one = unsigned_block_header_one[:11]
    rlp_unsigned_block_header_one = rlp.encode(unsigned_block_header_one)
    rlp_unsigned_block_header_two = two_equivocating_block_header[1]

    signature_one = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_one
    ).to_bytes()
    signature_two = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_two
    ).to_bytes()

    return (
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_one),
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_two),
    )


@pytest.fixture
def two_signed_blocks_different_signer(
    two_equivocating_block_header, malicious_validator_key, malicious_non_validator_key
):

    """Test data with two blocks which fulfill all equivocation rules, except they are have two different signers."""

    rlp_unsigned_block_header_one = two_equivocating_block_header[0]
    rlp_unsigned_block_header_two = two_equivocating_block_header[1]

    signature_one = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_one
    ).to_bytes()
    signature_two = malicious_non_validator_key.sign_msg(
        rlp_unsigned_block_header_two
    ).to_bytes()

    return (
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_one),
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_two),
    )


@pytest.fixture
def two_signed_blocks_different_block_step(
    two_equivocating_block_header, malicious_validator_key, timestamp_outside_step
):

    """Test data with two blocks which fulfill all equivocation rules except the block step.

    Note that this fixture is using a parametrized timestamp value.
    """

    unsigned_block_header_one = rlp.decode(two_equivocating_block_header[0])
    unsigned_block_header_one[11] = timestamp_outside_step
    rlp_unsigned_block_header_one = rlp.encode(unsigned_block_header_one)

    rlp_unsigned_block_header_two = two_equivocating_block_header[1]

    signature_one = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_one
    ).to_bytes()
    signature_two = malicious_validator_key.sign_msg(
        rlp_unsigned_block_header_two
    ).to_bytes()

    return (
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_one),
        SignedBlockHeader(rlp_unsigned_block_header_two, signature_two),
    )
