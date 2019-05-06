import pytest

import re
from click.testing import CliRunner

from auction_deploy.cli import main


@pytest.fixture()
def runner():
    return CliRunner()


@pytest.fixture
def deployed_auction_address(runner):

    deploy_result = runner.invoke(
        main, args="deploy --release-block 789123 --jsonrpc test"
    )

    lines = deploy_result.output.split("\n")
    for line in lines:
        match = re.match("^Auction address: (0x[0-9a-fA-F]{40})$", line)
        if match:
            return match[1]

    print("Output:", lines)
    assert False, "Could not find auction address in output"


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


def test_cli_start_auction(runner, deployed_auction_address):

    result = runner.invoke(
        main,
        args="start-auction --jsonrpc test --auction-address "
        + deployed_auction_address,
    )

    assert result.exit_code == 0


def test_cli_start_auction_with_auto_nonce(
    runner, deployed_auction_address, keystores, key_password
):
    """test the auto-nonce option. we only do this for the start-auction"""

    result = runner.invoke(
        main,
        args=f"start-auction --auto-nonce --jsonrpc test --keystore {keystores[0]}"
        + f" --auction-address {deployed_auction_address}",
        input=key_password,
    )
    print(result.output)
    assert result.exit_code == 0


def test_cli_start_auction_key_not_owner(
    runner, deployed_auction_address, keystore_file_path, key_password
):
    """Test that when you attempt to start the auction with a private_key not corresponding to the
    owner of the auction, the command fails
    This shows that the command takes into account the key"""

    result = runner.invoke(
        main,
        args="start-auction --jsonrpc test --auction-address "
        + deployed_auction_address
        + " --keystore "
        + str(keystore_file_path),
        input=key_password,
    )

    assert result.exit_code == 1


def test_cli_auction_status(runner, deployed_auction_address):

    result = runner.invoke(
        main,
        args="print-auction-status --jsonrpc test --auction-address "
        + deployed_auction_address,
    )

    assert result.exit_code == 0


def test_cli_not_checksummed_address(runner, deployed_auction_address):

    address = deployed_auction_address.lower()

    result = runner.invoke(
        main, args=f"print-auction-status --jsonrpc test --auction-address {address}"
    )

    assert result.exit_code == 0


def test_cli_incorrect_address_parameter_fails(runner):

    not_an_address = "not_an_address"

    result = runner.invoke(
        main,
        args=f"print-auction-status --jsonrpc test --auction-address {not_an_address}",
    )

    assert (
        f"The address parameter is not recognized to be an address: {not_an_address}"
        in result.output
    )
    assert result.exit_code == 2
