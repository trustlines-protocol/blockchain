import pytest

from auction_deploy.core import (
    AuctionOptions,
    DeployedAuctionContracts,
    DeployedContractsAddresses,
    deploy_auction_contracts,
    initialize_auction_contracts,
    missing_whitelisted_addresses,
    whitelist_addresses,
)


@pytest.fixture()
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
    if auction_options.token_address is not None:
        assert (
            deployed_contracts.auction.functions.bidToken().call()
            == auction_options.token_address
        )

    assert deployed_contracts.locker.functions.initialized().call() is False

    assert deployed_contracts.slasher is not None
    assert deployed_contracts.slasher.functions.initialized().call() is False


@pytest.fixture(params=[True, False])
def already_deployed_auction_address(request, deployed_contracts):
    if request.param:
        return deployed_contracts.auction.address
    else:
        return None


@pytest.fixture(params=[True, False])
def already_deployed_locker_address(request, deployed_contracts):
    if request.param:
        return deployed_contracts.locker.address
    else:
        return None


@pytest.fixture(params=[True, False])
def already_initialized_locker_contract(
    request, deployed_contracts, use_token, token_contract
):
    if request.param:
        locker_init_args = (
            2000000000,
            deployed_contracts.slasher.address,
            deployed_contracts.auction.address,
        )
        if use_token:
            locker_init_args += (token_contract.address,)
        deployed_contracts.locker.functions.init(*locker_init_args).transact()
    return deployed_contracts.locker


@pytest.fixture(params=[True, False])
def already_deployed_slasher_address(request, deployed_contracts):
    if request.param:
        return deployed_contracts.slasher.address
    else:
        return None


@pytest.fixture(params=[True, False])
def already_initialized_slasher_contract(request, deployed_contracts):
    if request.param:
        deployed_contracts.slasher.functions.init(
            deployed_contracts.locker.address
        ).transact()
    return deployed_contracts.slasher


@pytest.fixture()
def already_deployed_contract_addresses(
    already_deployed_auction_address,
    already_deployed_locker_address,
    already_deployed_slasher_address,
):
    """Returns every possible combinations of deployed / empty auction related contracts"""
    return DeployedContractsAddresses(
        auction=already_deployed_auction_address,
        locker=already_deployed_locker_address,
        slasher=already_deployed_slasher_address,
    )


@pytest.fixture()
def already_initialized_contract_addresses(
    deployed_contracts,
    already_initialized_locker_contract,
    already_initialized_slasher_contract,
):
    """Returns every possible combinations of initialized/non-initialized auction related contracts"""
    return DeployedAuctionContracts(
        auction=deployed_contracts.auction,
        locker=already_initialized_locker_contract,
        slasher=already_initialized_slasher_contract,
    )


def test_resume_deploy_contracts(
    web3, auction_options, already_deployed_contract_addresses
):
    if (
        already_deployed_contract_addresses.auction is not None
        and already_deployed_contract_addresses.locker is None
    ):
        with pytest.raises(ValueError):
            deploy_auction_contracts(
                web3=web3,
                auction_options=auction_options,
                already_deployed_contracts=already_deployed_contract_addresses,
            )
    else:
        deployed_contracts: DeployedAuctionContracts = deploy_auction_contracts(
            web3=web3,
            auction_options=auction_options,
            already_deployed_contracts=already_deployed_contract_addresses,
        )

        if already_deployed_contract_addresses.auction is not None:
            assert (
                deployed_contracts.auction.address
                == already_deployed_contract_addresses.auction
            )
        if already_deployed_contract_addresses.locker is not None:
            assert (
                deployed_contracts.locker.address
                == already_deployed_contract_addresses.locker
            )
        if already_deployed_contract_addresses.slasher is not None:
            assert (
                deployed_contracts.slasher.address
                == already_deployed_contract_addresses.slasher
            )


def test_init_contracts(deployed_contracts, web3, release_timestamp, auction_options):

    initialize_auction_contracts(
        web3=web3,
        contracts=deployed_contracts,
        release_timestamp=release_timestamp,
        token_address=auction_options.token_address,
    )

    assert deployed_contracts.locker.functions.initialized().call() is True
    assert deployed_contracts.slasher.functions.initialized().call() is True


def test_resume_init_contracts(
    already_initialized_contract_addresses, web3, release_timestamp, auction_options
):
    initialize_auction_contracts(
        web3=web3,
        contracts=already_initialized_contract_addresses,
        release_timestamp=release_timestamp,
        token_address=auction_options.token_address,
    )

    assert (
        already_initialized_contract_addresses.locker.functions.initialized().call()
        is True
    )
    assert (
        already_initialized_contract_addresses.slasher.functions.initialized().call()
        is True
    )


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
