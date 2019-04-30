import pytest
from click.testing import CliRunner

from auction_deploy.cli import main


@pytest.fixture()
def runner():
    return CliRunner()


def test_cli_contract_parameters_set(runner):

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


def test_cli_private_key(runner, keystore_file_path, key_password):

    result = runner.invoke(
        main,
        args="deploy --jsonrpc test --release-block 789123 --keystore "
        + str(keystore_file_path),
        input=key_password,
    )

    assert result.exit_code == 0
