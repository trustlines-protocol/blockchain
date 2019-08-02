import json
import os

import eth_tester
import pytest
from eth_keyfile import create_keyfile_json
from eth_utils import to_canonical_address

from auction_deploy.core import AuctionOptions

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses for the validator auction in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6

RELEASE_TIMESTAMP_OFFSET = 3600 * 24 * 180


def remove_click_options_environment_variables():
    """remove the environment variables used by click options in the CLI.
    Otherwise they will interfere with the tests
    """
    for env_var in list(os.environ.keys()):
        if env_var.startswith("AUCTION_DEPLOY_"):
            del os.environ[env_var]


remove_click_options_environment_variables()


def create_address_string(i: int):
    return f"0x{str(i).rjust(40, '0')}"


@pytest.fixture()
def keystores(tmp_path, account_keys, key_password):
    """paths to keystore files"""
    paths = []
    for i, private_key in enumerate(account_keys[:2]):
        file_path = tmp_path / f"keyfile-{i}.json"
        file_path.write_text(
            json.dumps(
                create_keyfile_json(
                    private_key.to_bytes(), key_password.encode("utf-8")
                )
            )
        )
        paths.append(file_path)

    return paths


@pytest.fixture()
def keystore_file_path(tmp_path, keystores, key_password):
    """path to keystore of account[1]"""
    return keystores[1]


@pytest.fixture()
def key_password():
    """password used for the keystores"""
    return "test_password"


@pytest.fixture()
def private_key(account_keys):
    """private key of account[1]"""
    return account_keys[1]


@pytest.fixture()
def whitelist():
    return [to_canonical_address(create_address_string(i)) for i in range(30)]


@pytest.fixture
def release_timestamp(web3):
    """release timestamp used for DepositLocker contract"""
    now = web3.eth.getBlock("latest").timestamp
    return now + RELEASE_TIMESTAMP_OFFSET


@pytest.fixture
def auction_options(release_timestamp):
    start_price = 1
    auction_duration = 2
    minimal_number_of_participants = 3
    maximal_number_of_participants = 4

    contract_options = AuctionOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        minimal_number_of_participants=minimal_number_of_participants,
        maximal_number_of_participants=maximal_number_of_participants,
        release_timestamp=release_timestamp,
    )

    return contract_options
