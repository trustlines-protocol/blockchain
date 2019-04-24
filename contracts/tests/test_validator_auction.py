#! pytest

import pytest
import eth_tester.exceptions
import time
from enum import Enum

from .conftest import AUCTION_START_PRICE, AUCTION_DURATION_IN_DAYS

TWO_WEEKS_IN_SECONDS = 14 * 24 * 60 * 60
ONE_HOUR_IN_SECONDS = 60 * 60
ETH_IN_WEI = 1e18

TEST_PRICE = 100


# This has to be in sync with the AuctionStates in ValidatorAuction.sol
class AuctionState(Enum):
    Deployed = 0
    Started = 1
    DepositPending = 2
    Ended = 3
    Failed = 4


def assert_auction_state(validator_contract, expected_auction_state):
    """assert that the current auctionState() of validator_contract is expected_auction_state"""
    assert expected_auction_state == AuctionState(
        validator_contract.functions.auctionState().call()
    ), "wrong auction state, make sure test_validator_auction.AuctionState is in sync with contracts"


def time_travel_to_end_of_auction(chain):
    chain.time_travel(int(time.time()) + TWO_WEEKS_IN_SECONDS + 10000)
    # It appears that the estimation of whether a transaction will fail is done on the latest block
    # while estimating gas cost for the transaction.
    # If we do not mine a block, the estimation will consider the wrong block time.
    chain.mine_block()


@pytest.fixture()
def started_validator_auction(validator_auction_contract, accounts):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    return validator_auction_contract


@pytest.fixture()
def deposit_pending_validator_auction(almost_filled_validator_auction, accounts):
    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": 100}
    )

    assert_auction_state(almost_filled_validator_auction, AuctionState.DepositPending)

    return almost_filled_validator_auction


def test_auction_state_deployed(validator_auction_contract):
    assert_auction_state(validator_auction_contract, AuctionState.Deployed)


def test_cannot_bid_when_not_started(validator_auction_contract, accounts):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_auction_contract.functions.bid().transact(
            {"from": accounts[1], "value": TEST_PRICE}
        )


def test_auction_start_deposit_not_init(
    deploy_contract, non_initialized_deposit_locker_contract_session
):
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice",
        constructor_args=(non_initialized_deposit_locker_contract_session.address,),
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.startAuction().transact({})


def test_auction_start(validator_auction_contract, accounts, web3):

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    start_time = web3.eth.getBlock("latest").timestamp

    assert validator_auction_contract.functions.startTime().call() == start_time
    assert_auction_state(validator_auction_contract, AuctionState.Started)


def test_auction_start_not_owner(validator_auction_contract, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        validator_auction_contract.functions.startAuction().transact(
            {"from": accounts[1]}
        )


def test_bidding_not_whitelisted(started_validator_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[0], "value": TEST_PRICE}
        )


def test_bidding_bid_below_current_price(started_validator_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": TEST_PRICE - 1}
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
            {"from": accounts[1], "value": TEST_PRICE}
        )


def test_already_bid(started_validator_auction, accounts):

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": TEST_PRICE}
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": TEST_PRICE}
        )


def test_auction_failed(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    assert_auction_state(started_validator_auction, AuctionState.Failed)


def test_bidding_auction_failed(started_validator_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    started_validator_auction.functions.closeAuction().transact({"from": accounts[2]})

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        started_validator_auction.functions.bid().transact(
            {"from": accounts[1], "value": TEST_PRICE}
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
            {"from": accounts[1], "value": TEST_PRICE}
        )


@pytest.mark.slow
def test_enough_bidders_ends_auction(almost_filled_validator_auction, accounts):

    assert_auction_state(almost_filled_validator_auction, AuctionState.Started)

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": TEST_PRICE}
    )

    assert_auction_state(almost_filled_validator_auction, AuctionState.DepositPending)


@pytest.mark.slow
def test_send_bids_to_locker(
    deposit_pending_validator_auction, accounts, web3, number_of_auction_participants
):
    deposit_locker = deposit_pending_validator_auction.functions.depositLocker().call()
    assert web3.eth.getBalance(deposit_locker) == 0

    pre_balance = web3.eth.getBalance(deposit_pending_validator_auction.address)
    deposit_pending_validator_auction.functions.depositBids().transact(
        {"from": accounts[5]}
    )
    post_balance = web3.eth.getBalance(deposit_pending_validator_auction.address)
    total_price = (
        number_of_auction_participants
        * deposit_pending_validator_auction.functions.closingPrice().call()
    )
    assert post_balance == pre_balance - total_price
    assert web3.eth.getBalance(deposit_locker) == total_price
    assert_auction_state(deposit_pending_validator_auction, AuctionState.Ended)


@pytest.mark.slow
def test_withdraw_overbid(almost_filled_validator_auction, accounts, web3):

    value_to_bid = 1234

    almost_filled_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": value_to_bid}
    )

    almost_filled_validator_auction.functions.depositBids().transact(
        {"from": accounts[0]}
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

    almost_filled_validator_auction.functions.depositBids().transact(
        {"from": accounts[0]}
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
        {"from": accounts[1], "value": TEST_PRICE}
    )

    event = started_validator_auction.events.BidSubmitted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    bid_time = web3.eth.getBlock("latest").timestamp

    assert event["bidder"] == accounts[1]
    assert event["bidValue"] == TEST_PRICE
    assert event["timestamp"] == bid_time


def test_event_auction_started(validator_auction_contract, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    validator_auction_contract.functions.startAuction().transact({"from": accounts[0]})

    start_time = web3.eth.getBlock("latest").timestamp

    event = validator_auction_contract.events.AuctionStarted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["startTime"] == start_time


def test_event_auction_deployed(
    real_price_validator_auction_contract, number_of_auction_participants
):
    event_args = real_price_validator_auction_contract.events.AuctionDeployed.createFilter(
        fromBlock=0
    ).get_all_entries()[
        0
    ][
        "args"
    ]

    assert event_args["startPrice"] == AUCTION_START_PRICE
    assert event_args["auctionDurationInDays"] == AUCTION_DURATION_IN_DAYS
    assert event_args["numberOfParticipants"] == number_of_auction_participants


def test_event_auction_failed(started_validator_auction, accounts, chain, web3):

    started_validator_auction.functions.bid().transact(
        {"from": accounts[1], "value": TEST_PRICE}
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
    assert event["closingPrice"] == TEST_PRICE


def test_event_whitelist(no_whitelist_validator_auction_contract, whitelist, web3):

    no_whitelist_validator_auction_contract.functions.addToWhitelist(
        whitelist
    ).transact()

    latest_block_number = web3.eth.blockNumber

    events = no_whitelist_validator_auction_contract.events.AddressWhitelisted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()

    assert len(events) == len(whitelist)
    for i, event in enumerate(events):
        assert event["args"]["whitelistedAddress"] == whitelist[i]


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
    relative_auction_time = ms_since_start / AUCTION_DURATION_IN_DAYS
    decay_divisor = 746571428571
    decay = relative_auction_time ** 3 / decay_divisor
    price = (
        AUCTION_START_PRICE
        * (1 + relative_auction_time)
        / (1 + relative_auction_time + decay)
    )

    return price


def pytest_generate_tests(metafunc):
    arg_values = generate_price_test_data()
    if (
        "hours_since_start" in metafunc.fixturenames
        and "python_price" in metafunc.fixturenames
    ):
        metafunc.parametrize(["hours_since_start", "python_price"], arg_values)


@pytest.mark.slow
def test_against_python_price_function(
    real_price_validator_auction_contract, hours_since_start, python_price, accounts
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )

    seconds_since_start = ONE_HOUR_IN_SECONDS * hours_since_start

    blockchain_price = real_price_validator_auction_contract.functions.priceAtElapsedTime(
        seconds_since_start
    ).call()

    assert blockchain_price == pytest.approx(python_price, abs=1e16)


@pytest.mark.parametrize(
    "hours_since_start, price_min, price_max",
    [
        (0, AUCTION_START_PRICE, AUCTION_START_PRICE),
        (AUCTION_DURATION_IN_DAYS * 24 // 2, 3 * ETH_IN_WEI, 4 * ETH_IN_WEI),
        (AUCTION_DURATION_IN_DAYS * 24, 1 * ETH_IN_WEI, 2 * ETH_IN_WEI),
    ],
)
def test_price(
    real_price_validator_auction_contract,
    hours_since_start,
    price_min,
    price_max,
    accounts,
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )

    seconds_since_start = ONE_HOUR_IN_SECONDS * hours_since_start

    blockchain_price = real_price_validator_auction_contract.functions.priceAtElapsedTime(
        seconds_since_start
    ).call()

    assert price_min <= blockchain_price <= price_max


def test_bid_real_price_auction(
    real_price_validator_auction_contract, accounts, chain, web3
):

    real_price_validator_auction_contract.functions.startAuction().transact(
        {"from": accounts[0]}
    )
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # Need to mine a block after time travel to make the call consider the new block time.
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
    # Need to mine a block after time travel to make the call consider the new block time.
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
