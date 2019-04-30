import pytest

from auction_deploy.core import (
    deploy_auction_contracts,
    AuctionOptions,
    DeployedAuctionContracts,
    initialize_auction_contracts,
    decrypt_private_key,
)


@pytest.fixture
def deployed_contracts(web3):
    start_price = 1
    auction_duration = 2
    number_of_participants = 3
    release_block_number = 1234

    contract_options = AuctionOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        number_of_participants=number_of_participants,
        release_block_number=release_block_number,
    )

    deployed_contracts: DeployedAuctionContracts = deploy_auction_contracts(
        web3=web3, auction_options=contract_options
    )

    return deployed_contracts


def test_deploy_contracts(web3):

    start_price = 1
    auction_duration = 2
    number_of_participants = 3
    release_block_number = 1234

    contract_options = AuctionOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        number_of_participants=number_of_participants,
        release_block_number=release_block_number,
    )

    deployed_contracts: DeployedAuctionContracts = deploy_auction_contracts(
        web3=web3, auction_options=contract_options
    )

    assert deployed_contracts.auction.functions.startPrice().call() == start_price
    assert (
        deployed_contracts.auction.functions.auctionDurationInDays().call()
        == auction_duration
    )
    assert (
        deployed_contracts.auction.functions.numberOfParticipants().call()
        == number_of_participants
    )

    assert deployed_contracts.locker.functions.initialized().call() is False

    assert deployed_contracts.slasher.functions.initialized().call() is False


def test_init_contracts(deployed_contracts, web3):

    release_block_number = 123456

    initialize_auction_contracts(
        web3=web3,
        contracts=deployed_contracts,
        release_block_number=release_block_number,
    )

    assert deployed_contracts.locker.functions.initialized().call() is True
    assert deployed_contracts.slasher.functions.initialized().call() is True


def test_decrypt_private_key(keystore_file_path, key_password, private_key):
    extracted_key = decrypt_private_key(str(keystore_file_path), key_password)
    assert extracted_key == private_key
