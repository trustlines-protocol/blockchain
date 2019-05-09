import csv

import pytest

import re
from click.testing import CliRunner
from eth_utils import to_checksum_address

from auction_deploy.cli import main, test_provider, test_json_rpc, AuctionState
from auction_deploy.core import (
    get_deployed_auction_contracts,
    DeployedAuctionContracts,
    deploy_auction_contracts,
)


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture()
def deployed_auction_address(runner):
    """Deploys an auction and return its address"""
    number_of_participants = 2
    starting_price = 1

    deploy_result = runner.invoke(
        main,
        args=f"deploy --release-timestamp 2000000000 --max-participants {number_of_participants}"
        f" --min-participants {number_of_participants - 1}"
        f" --start-price {starting_price} --jsonrpc test",
    )

    lines = deploy_result.output.split("\n")
    for line in lines:
        match = re.match("^Auction address: (0x[0-9a-fA-F]{40})$", line)
        if match:
            return match[1]

    raise ValueError(f"Could not find auction address in output: {lines}")


@pytest.fixture()
def whitelisted_auction_address(runner, deployed_auction_address, whitelist_file):
    """Whitelists all addresses in the whitelist on the deployed auction and returns its address"""

    runner.invoke(
        main,
        args=f"whitelist --file {whitelist_file} --address {deployed_auction_address} "
        + "--batch-size 100 --jsonrpc test",
    )

    return deployed_auction_address


@pytest.fixture()
def whitelist_file(tmp_path, key_password, whitelist):
    folder = tmp_path / "subfolder"
    folder.mkdir()
    file_path = folder / "whitelist.csv"

    with file_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerows([[to_checksum_address(address)] for address in whitelist])

    return file_path


@pytest.fixture
def contracts(deployed_auction_address) -> DeployedAuctionContracts:
    """return the core.DeployedAuctionContracts object for the currently active auction"""
    return get_deployed_auction_contracts(test_json_rpc, deployed_auction_address)


@pytest.fixture
def contracts_not_initialized(auction_options) -> DeployedAuctionContracts:
    """return the three auction related contracts where locker and slasher are not initialized"""

    contracts = deploy_auction_contracts(
        web3=test_json_rpc, auction_options=auction_options
    )

    return contracts


@pytest.fixture
def ensure_auction_state(contracts):
    """return a function that can be used to check the current auction state"""

    def ensure_state(expected_state):
        current_state = AuctionState(contracts.auction.functions.auctionState().call())
        assert current_state == expected_state

    return ensure_state


@pytest.fixture
def ether_owning_whitelist(accounts):
    return [accounts[1], accounts[2]]


@pytest.fixture
def deposit_pending_auction(
    runner,
    deployed_auction_address,
    contracts,
    ether_owning_whitelist,
    ensure_auction_state,
):
    """return the auction contract with enough bids so that the state is `DepositPending`"""

    contracts.auction.functions.addToWhitelist(ether_owning_whitelist).transact()
    contracts.auction.functions.startAuction().transact()

    bid_value = contracts.auction.functions.currentPrice().call()

    contracts.auction.functions.bid().transact(
        {"from": ether_owning_whitelist[0], "value": bid_value}
    )
    contracts.auction.functions.bid().transact(
        {"from": ether_owning_whitelist[1], "value": bid_value}
    )

    ensure_auction_state(AuctionState.DepositPending)
    return contracts.auction


def test_cli_contract_parameters_set(runner):

    result = runner.invoke(
        main,
        args="deploy --start-price 123 --duration 4 --max-participants 567 --min-participants 456 "
        "--release-timestamp 2000000000 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_transaction_parameters_set(runner):
    result = runner.invoke(
        main,
        args="deploy --nonce 0 --gas-price 123456789 --gas 7000000 --release-timestamp 2000000000 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_private_key(runner, keystore_file_path, key_password):

    result = runner.invoke(
        main,
        args="deploy --jsonrpc test --release-timestamp 2000000000 --keystore "
        + str(keystore_file_path),
        input=key_password,
    )

    assert result.exit_code == 0


def test_cli_start_auction(runner, deployed_auction_address):

    result = runner.invoke(
        main, args="start --jsonrpc test --address " + deployed_auction_address
    )

    assert result.exit_code == 0


def test_cli_close_auction(
    runner, deployed_auction_address, ensure_auction_state, contracts
):
    result = runner.invoke(
        main, args=f"start --jsonrpc test --address {deployed_auction_address}"
    )

    assert result.exit_code == 0

    auction_duration = (
        contracts.auction.functions.auctionDurationInDays().call() * 24 * 3600
    )

    # auction is started, time travel forward
    test_provider.ethereum_tester.time_travel(
        test_json_rpc.eth.getBlock("latest").timestamp + auction_duration
    )
    test_provider.ethereum_tester.mine_block()

    result = runner.invoke(
        main, args=f"close --jsonrpc test --address {deployed_auction_address}"
    )
    assert result.exit_code == 0
    ensure_auction_state(AuctionState.Failed)


def test_cli_start_auction_with_auto_nonce(
    runner, deployed_auction_address, keystores, key_password
):
    """test the auto-nonce option. we only do this for the start-auction"""

    result = runner.invoke(
        main,
        args=f"start --auto-nonce --jsonrpc test --keystore {keystores[0]}"
        + f" --address {deployed_auction_address}",
        input=key_password,
    )
    assert result.exit_code == 0


def test_cli_start_auction_key_not_owner(
    runner, deployed_auction_address, keystore_file_path, key_password
):
    """Test that when you attempt to start the auction with a private_key not corresponding to the
    owner of the auction, the command fails
    This shows that the command takes into account the key"""

    result = runner.invoke(
        main,
        args="start --jsonrpc test --address "
        + deployed_auction_address
        + " --keystore "
        + str(keystore_file_path),
        input=key_password,
    )
    assert result.exit_code == 1


def test_cli_deposit_bids(runner, deposit_pending_auction, ensure_auction_state):

    result = runner.invoke(
        main,
        args=f"deposit-bids --jsonrpc test --address {deposit_pending_auction.address}",
    )

    assert result.exit_code == 0
    ensure_auction_state(AuctionState.Ended)


def test_cli_auction_status(runner, deployed_auction_address):

    result = runner.invoke(
        main, args="status --jsonrpc test --address " + deployed_auction_address
    )
    assert result.exit_code == 0


def test_cli_auction_status_locker_not_init(runner, contracts_not_initialized):

    result = runner.invoke(
        main,
        args="status --jsonrpc test --address "
        + contracts_not_initialized.auction.address,
    )

    assert result.exit_code == 0


def test_cli_whitelist(runner, deployed_auction_address, whitelist_file, whitelist):
    result = runner.invoke(
        main,
        args=f"whitelist --file {whitelist_file} --address {deployed_auction_address} "
        + "--batch-size 10 --jsonrpc test",
    )
    assert result.exit_code == 0
    assert result.output == f"Number of whitelisted addresses: {len(whitelist)}\n"


def test_cli_check_whitelist_not_whitelisted(
    runner, deployed_auction_address, whitelist_file, whitelist
):
    result = runner.invoke(
        main,
        args=f"check-whitelist --file {whitelist_file} --address {deployed_auction_address} "
        + "--jsonrpc test",
    )
    assert result.exit_code == 0
    assert (
        result.output
        == f"{len(whitelist)} of {len(whitelist)} addresses have not been whitelisted yet\n"
    )


def test_cli_check_whitelist_all_whitelisted(
    runner, whitelisted_auction_address, whitelist_file, whitelist
):
    result = runner.invoke(
        main,
        args=f"check-whitelist --file {whitelist_file} --address {whitelisted_auction_address} "
        + "--jsonrpc test",
    )
    assert result.exit_code == 0
    assert result.output == f"All {len(whitelist)} addresses have been whitelisted\n"


def test_cli_not_checksummed_address(runner, deployed_auction_address):

    address = deployed_auction_address.lower()

    result = runner.invoke(main, args=f"status --jsonrpc test --address {address}")

    assert result.exit_code == 0


def test_cli_incorrect_address_parameter_fails(runner):

    not_an_address = "not_an_address"

    result = runner.invoke(
        main, args=f"status --jsonrpc test --address {not_an_address}"
    )

    assert (
        f"The address parameter is not recognized to be an address: {not_an_address}"
        in result.output
    )
    assert result.exit_code == 2
