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


@pytest.fixture
def deployed_auction_address(runner):

    deploy_result = runner.invoke(
        main, args="deploy --release-block 789123 --jsonrpc test"
    )

    for line in deploy_result.output.split("\n"):
        if line.startswith("Auction address:"):
            prefixed_address_length = 42
            auction_address = line[-prefixed_address_length:]

    return auction_address


def test_cli_auction_status(runner, deployed_auction_address):

    result = runner.invoke(
        main,
        args="print-auction-status --jsonrpc test --auction-address "
        + deployed_auction_address,
    )

    assert result.exit_code == 0
