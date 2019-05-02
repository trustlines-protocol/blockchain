from json import dumps

import pytest
import eth_tester
from eth_keyfile import create_keyfile_json

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses for the validator auction in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6


@pytest.fixture()
def keystore_file_path(tmp_path, key_password, private_key):
    folder = tmp_path / "subfolder"
    folder.mkdir()
    file_path = folder / "keyfile.json"

    key_file = create_keyfile_json(private_key.to_bytes(), key_password.encode("utf-8"))

    file_path.write_text(dumps(key_file))

    return file_path


@pytest.fixture()
def key_password():
    return "test_password"


@pytest.fixture()
def private_key(account_keys):
    return account_keys[1]
