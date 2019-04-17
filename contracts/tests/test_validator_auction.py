#! pytest

import pytest
import eth_tester.exceptions
import time
from enum import Enum

TWO_WEEKS_IN_SECONDS = 14 * 24 * 60 * 60


# This has to be in sync with the AuctionStates in ValidatorAuction.sol
class AuctionStates(Enum):
    Deployed = 0
    Started = 1
    Ended = 2
    Failed = 3


def assert_auction_state(validator_contract, expected_auction_state):
    """assert that the current auctionState() of validator_contract is expected_auction_state"""
    assert expected_auction_state == AuctionStates(
        validator_contract.functions.auctionState().call()
    ), "wrong auction state, make sure test_validator_auction.AuctionState is in sync with contracts"


def time_travel_to_end_of_auction(chain):
    chain.time_travel(int(time.time()) + TWO_WEEKS_IN_SECONDS + 10000)
    # It appears that if we do not mine a block, the time travel does not work properly.
    chain.mine_block()


@pytest.fixture()
def started_validator_auction(validator_auction_contract, accounts):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    return validator_auction_contract


def test_auction_state_deployed(validator_auction_contract):
    assert_auction_state(validator_auction_contract, AuctionStates.Deployed)


def test_cannot_bid_when_not_started(validator_auction_contract, accounts):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_auction_contract.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


def test_auction_start(validator_auction_contract, accounts, web3):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    start_time = web3.eth.getBlock("latest").timestamp

    assert validator_auction_contract.functions.startTime().call() == start_time
    assert_auction_state(validator_auction_contract, AuctionStates.Started)


def test_auction_start_not_owner(validator_auction_contract, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_auction_contract.functions.startAuction().transact(
            {"from": accounts[1]}
        )


def test_bidding_not_whitelisted(started_validator_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[0], "value": 100}
        )


def test_bidding_bid_below_current_price(started_validator_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": 99}
        )


def test_bidding(started_validator_auction, accounts):

    bid_value = 219

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": bid_value}
    )

    assert started_validator_auction.functions.bids(accounts[1]).call() == bid_value


def test_bidding_too_late(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


def test_already_bid(started_validator_auction, accounts):

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 100}
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


def test_auction_failed(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    assert_auction_state(started_validator_auction, AuctionStates.Failed)


def test_bidding_auction_failed(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


def test_close_auction_too_soon(started_validator_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.closeAuction().transact(
            {"from": accounts[2]}
        )


def test_bidding_auction_ended(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)

    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


@pytest.mark.slow
def test_enough_bidders_ends_auction(almost_filled_validator_auction, accounts):

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 100}
    )

    assert_auction_state(almost_filled_validator_auction, AuctionStates.Ended)


@pytest.mark.slow
def test_withdraw_overbid(almost_filled_validator_auction, accounts, web3):

    value_to_bid = 1234

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": value_to_bid}
    )

    pre_balance = web3.eth.getBalance(accounts[1], "latest")

    almost_filled_validator_auction.functions.withdraw().transact(
        {"from": accounts[1], "gasPrice": 0}
    )
    closing_price = almost_filled_validator_auction.functions.closingPrice().call()

    post_balance = web3.eth.getBalance(accounts[1], "latest")

    assert post_balance - pre_balance == value_to_bid - closing_price


def test_cannot_withdraw_too_soon(started_validator_auction, accounts):

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 1234}
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.withdraw().transact(
            {"from": accounts[1], "gasPrice": 0}
        )


@pytest.mark.slow
def test_cannot_withdraw_twice(almost_filled_validator_auction, accounts, web3):

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 1234}
    )

    almost_filled_validator_auction.functions.withdraw().transact(
        {"from": accounts[1], "gasPrice": 0}
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        almost_filled_validator_auction.functions.withdraw().transact(
            {"from": accounts[1]}
        )


def test_withdraw_auction_failed(started_validator_auction, accounts, chain, web3):

    value_to_bid = 1234

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": value_to_bid}
    )

    pre_balance = web3.eth.getBalance(accounts[1], "latest")

    time_travel_to_end_of_auction(chain)

    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    started_validator_auction.functions.withdraw().transact(
        {"from": accounts[1], "gasPrice": 0}
    )

    post_balance = web3.eth.getBalance(accounts[1], "latest")

    assert post_balance - pre_balance == value_to_bid


@pytest.mark.slow
def test_cannot_withdraw_overbid_not_bidder(almost_filled_validator_auction, accounts):

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 1234}
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        almost_filled_validator_auction.functions.withdraw().transact(
            {"from": accounts[0], "gasPrice": 0}
        )


def test_event_bid_submitted(started_validator_auction, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 100}
    )

    event = started_validator_auction.events.BidSubmitted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    bid_time = web3.eth.getBlock("latest").timestamp

    assert event["bidder"] == accounts[1]
    assert event["bidValue"] == 100
    assert event["timestamp"] == bid_time


def test_event_auction_started(validator_auction_contract, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    start_time = web3.eth.getBlock("latest").timestamp

    event = validator_auction_contract.events.AuctionStarted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["startTime"] == start_time


def test_event_auction_failed(started_validator_auction, accounts, chain, web3):

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 100}
    )

    time_travel_to_end_of_auction(chain)

    latest_block_number = web3.eth.blockNumber

    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    event = started_validator_auction.events.AuctionFailed.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    close_time = started_validator_auction.functions.closeTime().call()

    assert event["closeTime"] == close_time
    assert event["numberOfBidders"] == 1


@pytest.mark.slow
def test_event_auction_ended(almost_filled_validator_auction, accounts, chain, web3):

    latest_block_number = web3.eth.blockNumber

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 234}
    )

    close_time = web3.eth.getBlock("latest").timestamp

    event = almost_filled_validator_auction.events.AuctionEnded.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["closeTime"] == close_time
    assert event["closingPrice"] == 100
