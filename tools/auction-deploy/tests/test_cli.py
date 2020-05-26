import csv
import re

import pytest
from click.testing import CliRunner
from deploy_tools.cli import test_json_rpc, test_provider
from eth_tester.exceptions import TransactionFailed
from eth_utils import to_checksum_address

import auction_deploy.core
from auction_deploy.cli import AuctionState, main
from auction_deploy.core import (
    DeployedAuctionContracts,
    deploy_auction_contracts,
    get_deployed_auction_contracts,
)


@pytest.fixture
def runner():
    return CliRunner()


def extract_auction_address(output):
    """extract the auction address from 'deploy' output"""
    match = re.search("^Auction address: (0x[0-9a-fA-F]{40})$", output, re.M)
    if match:
        return match[1]

    raise ValueError(f"Could not find auction address in output: {repr(output)}")


@pytest.fixture()
def deployed_auction_address(auction_options, runner, use_token, token_contract):
    """Deploys an auction and return its address"""

    argument = (
        f"deploy --release-timestamp 2000000000 --max-participants "
        f"{auction_options.maximal_number_of_participants} "
        f"--min-participants {auction_options.minimal_number_of_participants}"
        f" --start-price {auction_options.start_price} --jsonrpc test"
    )

    if use_token:
        argument += f" --use-token --token-address {auction_options.token_address}"

    deploy_result = runner.invoke(main, args=argument)
    if deploy_result.exception is not None:
        raise RuntimeError(
            "Error while trying to run auction-deploy"
        ) from deploy_result.exception
    return extract_auction_address(deploy_result.output)


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
def whitelist_file(tmp_path, whitelist):
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


def bid(auction_contract, token_contract, sender, bid_value, use_token):
    if use_token:
        token_contract.functions.approve(auction_contract.address, bid_value).transact(
            {"from": sender}
        )
        auction_contract.functions.bid().transact({"from": sender})
    else:
        auction_contract.functions.bid().transact({"from": sender, "value": bid_value})


@pytest.fixture
def deposit_pending_auction(
    runner,
    deployed_auction_address,
    contracts,
    token_contract,
    auction_options,
    use_token,
    ether_owning_whitelist,
    ensure_auction_state,
):
    """return the auction contract with enough bids so that the state is `DepositPending`"""

    contracts.auction.functions.addToWhitelist(ether_owning_whitelist).transact()
    contracts.auction.functions.startAuction().transact()

    bid_value = contracts.auction.functions.currentPrice().call()

    bid(
        contracts.auction,
        token_contract,
        ether_owning_whitelist[0],
        bid_value,
        use_token,
    )
    bid(
        contracts.auction,
        token_contract,
        ether_owning_whitelist[1],
        bid_value,
        use_token,
    )

    ensure_auction_state(AuctionState.DepositPending)
    return contracts.auction


def test_cli_release_date_option(runner):
    deploy_result = runner.invoke(
        main, args="deploy --release-date '2033-05-18 03:33:21' --jsonrpc test"
    )
    assert deploy_result.exception is None
    assert deploy_result.exit_code == 0
    auction_address = extract_auction_address(deploy_result.output)
    contracts = get_deployed_auction_contracts(test_json_rpc, auction_address)
    release_timestamp = contracts.locker.functions.releaseTimestamp().call()
    # 2033-05-18 03:33:21 is timestamp 2000000001
    assert release_timestamp == 2_000_000_001


def test_cli_contract_parameters_set(runner):

    result = runner.invoke(
        main,
        args="deploy --start-price 123 --duration 4 --max-participants 567 --min-participants 456 "
        "--release-timestamp 2000000000 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_deploy_token_auction(runner):
    arbitrary_token_address = "0x" + "1234" * 10
    result = runner.invoke(
        main,
        args=f"deploy --use-token --token-address {arbitrary_token_address} --release-timestamp 2000000000 --jsonrpc test",
    )

    assert result.exit_code == 0


def test_cli_resume_deployment(runner, contracts_not_initialized):
    result = runner.invoke(
        main,
        args=f"deploy --start-price 123 --duration 4 --max-participants 567 --min-participants 456 "
        f"--release-timestamp 2000000000 --jsonrpc test --auction {contracts_not_initialized.auction.address}"
        f" --locker {contracts_not_initialized.locker.address}",
    )

    assert result.exit_code == 0
    assert (
        extract_auction_address(result.output)
        == contracts_not_initialized.auction.address
    )


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


@pytest.fixture()
def replace_bad_function_call_output():
    # TransactionFailed is raised by eth_tester
    # when BadFunctionCallOutput would be raised by web3 in `get_bid_token_address`
    bad_function_call = auction_deploy.core.BadFunctionCallOutput
    auction_deploy.core.BadFunctionCallOutput = TransactionFailed
    yield
    auction_deploy.core.BadFunctionCallOutput = bad_function_call


@pytest.mark.usefixtures("replace_bad_function_call_output")
def test_cli_auction_status(runner, deployed_auction_address):

    result = runner.invoke(
        main, args="status --jsonrpc test --address " + deployed_auction_address
    )
    assert result.exit_code == 0


@pytest.mark.usefixtures("replace_bad_function_call_output")
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


@pytest.mark.usefixtures("replace_bad_function_call_output")
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
