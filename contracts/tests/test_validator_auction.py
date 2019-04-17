#! pytest

import pytest
import eth_tester.exceptions
import time

TWO_WEEKS_IN_SECONDS = 14 * 24 * 60 * 60
ONE_HOUR_IN_SECONDS = 60 * 60


def time_travel_to_end_of_auction(chain):
    chain.time_travel(int(time.time()) + TWO_WEEKS_IN_SECONDS + 10000)
    # It appears that if we do not mine a block, the time travel does not work properly.
    chain.mine_block()


@pytest.fixture()
def started_validator_auction(validator_auction_contract, accounts):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    return validator_auction_contract


def test_auction_state_deployed(validator_auction_contract):
    assert validator_auction_contract.functions.auctionState().call() == 0


def test_cannot_bid_when_not_started(validator_auction_contract, accounts):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_auction_contract.functions.bid().transact(
            {"from": accounts[1], "value": 100}
        )


def test_auction_start(validator_auction_contract, accounts, web3):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    start_time = web3.eth.getBlock("latest").timestamp

    assert validator_auction_contract.functions.startTime().call() == start_time
    assert validator_auction_contract.functions.auctionState().call() == 1


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

    assert started_validator_auction.functions.auctionState().call() == 3


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

    assert almost_filled_validator_auction.functions.auctionState().call() == 2


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
def test_event_auction_ended(almost_filled_validator_auction, accounts, web3):

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


def generate_price_test_data():
    prices = []
    for i in range(0, 42 + 1):
        # Generate test data spanning 336 hours (= 2 weeks) across 43 tests.
        hours_since_start = 8 * i
        seconds_from_start = hours_since_start * ONE_HOUR_IN_SECONDS

        price = auction_price_at_elapsed_time(seconds_from_start)
        prices.append((hours_since_start, price))

    return prices


def auction_price_at_elapsed_time(seconds_from_start):
    ms_since_start = seconds_from_start * 1000
    starting_price = 10000 * 1e18
    decay_divisor = 146328000000000
    decay = ms_since_start ** 3 / decay_divisor
    price = starting_price * (1 + ms_since_start) / (1 + ms_since_start + decay)

    return price


def pytest_generate_tests(metafunc):
    arg_values = generate_price_test_data()
    if "hours_since_start" in metafunc.fixturenames:
        metafunc.parametrize(["hours_since_start", "python_price"], arg_values)


@pytest.mark.slow
def test_price_function(
    real_price_validator_auction_contract,
    hours_since_start,
    python_price,
    accounts,
    chain,
    web3,
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    seconds_since_start = ONE_HOUR_IN_SECONDS * hours_since_start

    if seconds_since_start != 0:
        chain.time_travel(start_time + seconds_since_start)
        # It appears that if we do not mine a block, the time travel does not work properly.
        chain.mine_block()

    blockchain_price = (
        real_price_validator_auction_contract.functions.currentPrice().call()
    )

    assert blockchain_price == pytest.approx(python_price, abs=1e15)


def test_bid_real_price_auction(
    real_price_validator_auction_contract, accounts, chain, web3
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # It appears that if we do not mine a block, the time travel does not work properly.
    chain.mine_block()

    price = real_price_validator_auction_contract.functions.currentPrice().call()

    real_price_validator_auction_contract.functions.bid().transact(
        {"from": accounts[1], "value": price}
    )


def test_too_low_bid_fails_real_price_auction(
    real_price_validator_auction_contract, accounts, chain, web3
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # It appears that if we do not mine a block, the time travel does not work properly.
    chain.mine_block()

    price_before_mining = (
        real_price_validator_auction_contract.functions.currentPrice().call()
    )
    chain.mine_block()
    price_after_mining = (
        real_price_validator_auction_contract.functions.currentPrice().call()
    )

    price_variation_on_block = price_before_mining - price_after_mining

    too_low_price = (
        real_price_validator_auction_contract.functions.currentPrice().call()
        - price_variation_on_block
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        real_price_validator_auction_contract.functions.bid().transact(
            {"from": accounts[1], "value": too_low_price}
        )
