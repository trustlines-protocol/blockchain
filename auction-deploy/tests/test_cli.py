import pytest
from click.testing import CliRunner
from eth_keyfile import create_keyfile_json

import sys
from contextlib import contextmanager

from json import dumps
from auction_deploy.cli import main, decrypt_private_key


@pytest.fixture()
def keystore_file(tmp_path, key_password, private_key):
    folder = tmp_path / "subfolder"
    folder.mkdir()
    file_path = folder / "keyfile.json"

    key_file = create_keyfile_json(private_key, key_password.encode("utf-8"))

    file_path.write_text(dumps(key_file))

    return file_path


@pytest.fixture()
def key_password():
    return "test_password"


@pytest.fixture()
def private_key():
    return (
        b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
        b"\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01\x01"
        b"\x01\x01\x01\x01\x01\x01"
    )


@pytest.fixture()
def runner():
    return CliRunner()


@contextmanager
def replace_stdin(target):
    orig = sys.stdin
    sys.stdin = target
    yield
    sys.stdin = orig


def test_cli_private_key(runner, keystore_file, key_password):

    result = runner.invoke(
        main, args="deploy --keystore " + str(keystore_file), input=key_password
    )

    assert result.exit_code == 0


def test_decrypt_private_key(keystore_file, key_password, private_key):
    extracted_key = decrypt_private_key(keystore_file, key_password)

    assert extracted_key == private_key
