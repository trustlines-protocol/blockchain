import pytest

from auction_deploy.cli import (
    deploy_contracts,
    ContractOptions,
    DeployedContracts,
    initialize_contracts,
)


@pytest.fixture
def private_key(account_keys):
    return account_keys[0]


@pytest.fixture
def deployed_contracts(web3):
    start_price = 1
    auction_duration = 2
    number_of_participants = 3
    release_block_number = 1234

    contract_options = ContractOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        number_of_participants=number_of_participants,
        release_block_number=release_block_number,
    )

    deployed_contracts: DeployedContracts = deploy_contracts(
        web3=web3, contract_options=contract_options
    )

    return deployed_contracts


def test_deploy_contracts(web3):

    start_price = 1
    auction_duration = 2
    number_of_participants = 3
    release_block_number = 1234

    contract_options = ContractOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        number_of_participants=number_of_participants,
        release_block_number=release_block_number,
    )

    deployed_contracts: DeployedContracts = deploy_contracts(
        web3=web3, contract_options=contract_options
    )

    assert deployed_contracts.auction.functions.startPrice().call() == start_price
    assert (
        deployed_contracts.auction.functions.auction_duration().call()
        == auction_duration
    )
    assert (
        deployed_contracts.auction.functions.number_of_participants().call()
        == number_of_participants
    )

    initial_number_of_depistors = 0
    assert (
        deployed_contracts.locker.functions.numberOfDepositors().call()
        == initial_number_of_depistors
    )

    assert deployed_contracts.slasher.functions.initialised().call() is False


def test_init_contracts(deployed_contracts, web3):

    release_block_number = 123456

    initialize_contracts(
        deployed_contracts.locker,
        release_block_number,
        deployed_contracts.slasher,
        web3,
    )

    assert (
        deployed_contracts.locker.functions.slasher().call()
        == deployed_contracts.slasher.address
    )
    assert (
        deployed_contracts.slasher.functions.depositContract().call()
        == deployed_contracts.locker.address
    )
