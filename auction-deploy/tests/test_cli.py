import pytest
from click.testing import CliRunner
from eth_keyfile import create_keyfile_json

from web3 import EthereumTesterProvider

from json import dumps
from auction_deploy.cli import main, decrypt_private_key


@pytest.fixture()
def keystore_file(tmp_path, key_password, private_key):
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
    return account_keys[0]


@pytest.fixture()
def runner():
    return CliRunner()


def test_cli_contract_parameters_set(runner, web3):

    print(EthereumTesterProvider)

    result = runner.invoke(
        main,
        args="deploy --start-price 123 --duration 4 --participants 567 --release-block 789123 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_transaction_parameters_set(runner):
    result = runner.invoke(
        main,
        args="deploy --nonce 0 --gas-price 123456789 --gas 7000000 --release-block 789123 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_private_key(runner, keystore_file, key_password):

    result = runner.invoke(
        main,
        args="deploy --jsonrpc test --release-block 789123 --keystore "
        + str(keystore_file),
        input=key_password,
    )

    assert result.exit_code == 0


def test_decrypt_private_key(keystore_file, key_password, private_key):
    extracted_key = decrypt_private_key(keystore_file, key_password)

    assert extracted_key == private_key
