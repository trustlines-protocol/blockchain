import pytest

from auction_deploy.core import (
    AuctionOptions,
    DeployedAuctionContracts,
    deploy_auction_contracts,
    initialize_auction_contracts,
    missing_whitelisted_addresses,
    whitelist_addresses,
)


@pytest.fixture
def deployed_contracts(web3, auction_options):

    deployed_contracts: DeployedAuctionContracts = deploy_auction_contracts(
        web3=web3, auction_options=auction_options
    )

    return deployed_contracts


def test_deploy_contracts(web3, auction_options: AuctionOptions):

    deployed_contracts: DeployedAuctionContracts = deploy_auction_contracts(
        web3=web3, auction_options=auction_options
    )

    assert (
        deployed_contracts.auction.functions.startPrice().call()
        == auction_options.start_price
    )
    assert (
        deployed_contracts.auction.functions.auctionDurationInDays().call()
        == auction_options.auction_duration
    )
    assert (
        deployed_contracts.auction.functions.minimalNumberOfParticipants().call()
        == auction_options.minimal_number_of_participants
    )
    assert (
        deployed_contracts.auction.functions.maximalNumberOfParticipants().call()
        == auction_options.maximal_number_of_participants
    )

    assert deployed_contracts.locker.functions.initialized().call() is False

    assert deployed_contracts.slasher.functions.initialized().call() is False


def test_init_contracts(deployed_contracts, web3, release_timestamp):

    initialize_auction_contracts(
        web3=web3, contracts=deployed_contracts, release_timestamp=release_timestamp
    )

    assert deployed_contracts.locker.functions.initialized().call() is True
    assert deployed_contracts.slasher.functions.initialized().call() is True


def test_whitelist_addresses(deployed_contracts, whitelist, web3):
    auction_contract = deployed_contracts.auction

    amount = whitelist_addresses(auction_contract, whitelist, batch_size=10, web3=web3)

    for address in whitelist:
        assert auction_contract.functions.whitelist(address).call() is True

    assert amount == len(whitelist)


def test_whitelist_addresses_with_nonce(
    deployed_contracts, whitelist, web3, default_account, account_keys
):
    auction_contract = deployed_contracts.auction

    nonce = web3.eth.getTransactionCount(default_account)

    whitelist_addresses(
        auction_contract,
        whitelist,
        batch_size=10,
        web3=web3,
        transaction_options={"nonce": nonce},
        private_key=account_keys[0],
    )

    for address in whitelist:
        assert auction_contract.functions.whitelist(address).call() is True


SPLIT_SIZE = 20


def test_whitelist_filter(deployed_contracts, whitelist, web3):

    auction_contract = deployed_contracts.auction

    assert missing_whitelisted_addresses(auction_contract, whitelist) == whitelist

    whitelist_addresses(
        auction_contract, whitelist[:SPLIT_SIZE], batch_size=10, web3=web3
    )

    assert (
        missing_whitelisted_addresses(auction_contract, whitelist)
        == whitelist[SPLIT_SIZE:]
    )


def test_whitelist_only_not_whitelisted(deployed_contracts, whitelist, web3):

    auction_contract = deployed_contracts.auction

    number1 = whitelist_addresses(
        auction_contract, whitelist[:SPLIT_SIZE], batch_size=10, web3=web3
    )
    assert number1 == SPLIT_SIZE

    number2 = whitelist_addresses(auction_contract, whitelist, batch_size=10, web3=web3)

    assert number2 == len(whitelist) - number1
