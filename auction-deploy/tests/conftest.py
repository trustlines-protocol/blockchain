import json

import pytest
import eth_tester
from eth_utils import to_canonical_address
from eth_keyfile import create_keyfile_json

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses for the validator auction in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6


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
    return [to_canonical_address(create_address_string(i)) for i in range(50)]
