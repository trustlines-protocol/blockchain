#! pytest

import time

import eth_tester.exceptions
import pytest

from .conftest import TEST_PRICE, AuctionState, assert_auction_state

TWO_WEEKS_IN_SECONDS = 14 * 24 * 60 * 60


def time_travel_to_end_of_auction(chain):
    chain.time_travel(int(time.time()) + TWO_WEEKS_IN_SECONDS + 10000)
    # It appears that the estimation of whether a transaction will fail is done on the latest block
    # while estimating gas cost for the transaction.
    # If we do not mine a block, the estimation will consider the wrong block time.
    chain.mine_block()


@pytest.fixture()
def token(auctionnable_token_contract):
    return auctionnable_token_contract


@pytest.fixture()
def auction_contract(token_validator_auction_contract):
    return token_validator_auction_contract


@pytest.fixture()
def started_auction_contract(token_validator_auction_contract, accounts):

    token_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )

    return token_validator_auction_contract


@pytest.fixture()
def almost_filled_auction(almost_filled_token_validator_auction):
    return almost_filled_token_validator_auction


@pytest.fixture()
def deposit_pending_filled_validator_auction(almost_filled_auction, token, accounts):
    """A validator auction with maximal number of bidders awaiting deposit transfer"""
    bid(almost_filled_auction, token, accounts[0])

    assert_auction_state(almost_filled_auction, AuctionState.DepositPending)

    return almost_filled_auction


@pytest.fixture()
def deposit_pending_almost_filled_validator_auction(
    almost_filled_auction, accounts, chain
):
    """A validator auction awaiting deposit transfer with a number of bidders below the maximal number of bidders"""

    time_travel_to_end_of_auction(chain)

    almost_filled_auction.functions.closeAuction().transact()

    assert_auction_state(almost_filled_auction, AuctionState.DepositPending)

    return almost_filled_auction


def bid(auction, token, sender, value=TEST_PRICE):
    token.functions.approve(auction.address, value).transact({"from": sender})
    auction.functions.bid().transact({"from": sender})


def test_cannot_bid_when_not_started(auction_contract, token, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(auction_contract, token, accounts[1])


def test_bidding_not_whitelisted(started_auction_contract, token, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(started_auction_contract, token, accounts[0])


def test_bidding_bid_below_current_price(started_auction_contract, token, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(started_auction_contract, token, accounts[1], TEST_PRICE - 1)


def test_bidding(started_auction_contract, token, accounts):

    bid_value = 123
    assert bid_value > TEST_PRICE

    bid(started_auction_contract, token, accounts[1], bid_value)

    assert started_auction_contract.functions.bids(accounts[1]).call() == TEST_PRICE


def test_bidding_too_late(started_auction_contract, token, accounts, chain):

    time_travel_to_end_of_auction(chain)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(started_auction_contract, token, accounts[1])


def test_already_bid(started_auction_contract, token, accounts):

    bid(started_auction_contract, token, accounts[1])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(started_auction_contract, token, accounts[1])


def test_bidding_auction_failed(started_auction_contract, token, accounts, chain):

    time_travel_to_end_of_auction(chain)
    started_auction_contract.functions.closeAuction().transact({"from": accounts[2]})

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(started_auction_contract, token, accounts[1])


@pytest.mark.slow
def test_enough_bidders_ends_auction(almost_filled_auction, token, accounts):

    assert_auction_state(almost_filled_auction, AuctionState.Started)

    bid(almost_filled_auction, token, accounts[1])

    assert_auction_state(almost_filled_auction, AuctionState.DepositPending)


def test_event_bid_submitted(started_auction_contract, token, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    bid(started_auction_contract, token, accounts[1])

    event = started_auction_contract.events.BidSubmitted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    bid_time = web3.eth.getBlock("latest").timestamp

    assert event["bidder"] == accounts[1]
    assert event["bidValue"] == TEST_PRICE
    assert event["timestamp"] == bid_time


def test_bid_real_price_auction(
    real_price_token_validator_auction_contract, token, accounts, chain, web3
):

    real_price_token_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # Need to mine a block after time travel to make the call consider the new block time.
    chain.mine_block()

    price = real_price_token_validator_auction_contract.functions.currentPrice().call()

    bid(real_price_token_validator_auction_contract, token, accounts[1], price)


def test_too_low_bid_fails_real_price_auction(
    real_price_token_validator_auction_contract, token, accounts, chain, web3
):

    real_price_token_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # Need to mine a block after time travel to make the call consider the new block time.
    chain.mine_block()

    price_before_mining = (
        real_price_token_validator_auction_contract.functions.currentPrice().call()
    )
    chain.mine_block()
    price_after_mining = (
        real_price_token_validator_auction_contract.functions.currentPrice().call()
    )

    price_variation_on_block = price_before_mining - price_after_mining

    # To bid, we need to `approve` on the token first, which will mine a block
    # so we need to subtract twice the price variation on block
    too_low_price = (
        real_price_token_validator_auction_contract.functions.currentPrice().call()
        - price_variation_on_block * 2
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        bid(
            real_price_token_validator_auction_contract,
            token,
            accounts[1],
            too_low_price,
        )
