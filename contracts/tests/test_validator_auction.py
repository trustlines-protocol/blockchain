#! pytest

import time
from enum import Enum
from typing import Any, Optional

import attr
import eth_tester.exceptions
import pytest
from tests.conftest import AUCTION_DURATION_IN_DAYS, AUCTION_START_PRICE, TEST_PRICE

TWO_WEEKS_IN_SECONDS = 14 * 24 * 60 * 60
ONE_HOUR_IN_SECONDS = 60 * 60
ETH_IN_WEI = 1e18


# This has to be in sync with the AuctionStates in ValidatorAuction.sol
class AuctionState(Enum):
    Deployed = 0
    Started = 1
    DepositPending = 2
    Ended = 3
    Failed = 4


@attr.s(auto_attribs=True)
class TestEnv:
    web3: Any
    auction: Any
    token: Optional[Any]

    @property
    def use_token(self):
        return self.token is not None

    @property
    def auction_start_time(self):
        return self.auction.functions.startTime().call()

    @property
    def current_price(self):
        return self.auction.functions.currentPrice().call()

    @property
    def lowest_slot_price(self):
        return self.auction.functions.lowestSlotPrice().call()

    @property
    def close_time(self):
        return self.auction.functions.closeTime().call()

    @property
    def deposit_locker_address(self):
        return self.auction.functions.depositLocker().call()

    @property
    def auction_balance(self):
        return self.balance_of(self.auction.address)

    @property
    def deposit_locker_balance(self):
        return self.balance_of(self.deposit_locker_address)

    def assert_auction_state(self, expected_auction_state):
        """assert that the current auctionState() of auctcion is expected_auction_state"""
        assert expected_auction_state == AuctionState(
            self.auction.functions.auctionState().call()
        ), "wrong auction state, make sure test_validator_auction.AuctionState is in sync with contracts"

    def bid(self, bidder, value):
        if self.use_token:
            self.token.functions.approve(self.auction.address, value).transact(
                {"from": bidder}
            )
            tx_hash = self.auction.functions.bid().transact({"from": bidder})
        else:
            tx_hash = self.auction.functions.bid().transact(
                {"from": bidder, "value": value}
            )
        return tx_hash

    def withdraw(self, sender):
        # Use 0 gas price to avoid having to take into account the consumed gas for tests on balances after withdraw
        self.auction.functions.withdraw().transact({"from": sender, "gasPrice": 0})

    def get_bid(self, bidder):
        return self.auction.functions.bids(bidder).call()

    def get_price_at_elapsed_time(self, seconds_since_start):
        return self.auction.functions.priceAtElapsedTime(seconds_since_start).call()

    def start_auction(self, sender=None):
        send_transaction_with_optional_sender(
            self.auction.functions.startAuction(), sender
        )

    def close_auction(self, sender=None):
        send_transaction_with_optional_sender(
            self.auction.functions.closeAuction(), sender
        )

    def deposit_bids(self, sender=None):
        send_transaction_with_optional_sender(
            self.auction.functions.depositBids(), sender
        )

    def balance_of(self, account):
        if self.use_token:
            return self.token.functions.balanceOf(account).call()
        else:
            return self.web3.eth.getBalance(account)


def send_transaction_with_optional_sender(transaction, sender=None):
    transaction_options = {"from": sender} if sender else {}
    transaction.transact(transaction_options)


@pytest.fixture(scope="session", params=["ValidatorAuction", "TokenValidatorAuction"])
def testenv(
    request,
    make_requested_testenv_for_contracts,
    validator_auction_contract,
    token_validator_auction_contract,
    auctionnable_token_contract,
) -> TestEnv:
    """return an initialized TestEnv instance"""

    return make_requested_testenv_for_contracts(
        request=request,
        eth_auction=validator_auction_contract,
        token_auction=token_validator_auction_contract,
        token=auctionnable_token_contract,
    )


@pytest.fixture()
def testenv_started_auction(
    testenv, make_requested_testenv_for_contracts, accounts
) -> TestEnv:
    """return a TestEnv instance where the auction is started"""
    testenv.start_auction(accounts[0])
    return testenv


@pytest.fixture(scope="session", params=["ValidatorAuction", "TokenValidatorAuction"])
def testenv_almost_filled_auction(
    request,
    make_requested_testenv_for_contracts,
    almost_filled_validator_auction,
    almost_filled_token_validator_auction,
    auctionnable_token_contract,
) -> TestEnv:
    """return a TestEnv instance where the auction is missing one bid to reach the maximum amount of bidders
    account[1] has not bid and can be used to test the behaviour of sending the last bid"""

    return make_requested_testenv_for_contracts(
        request=request,
        eth_auction=almost_filled_validator_auction,
        token_auction=almost_filled_token_validator_auction,
        token=auctionnable_token_contract,
    )


@pytest.fixture()
def testenv_deposit_pending_auction(testenv_almost_filled_auction, accounts) -> TestEnv:
    """A testenv with auction awaiting deposit transfer with maximal number of bidders"""
    testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE)
    testenv_almost_filled_auction.assert_auction_state(AuctionState.DepositPending)
    return testenv_almost_filled_auction


@pytest.fixture()
def testenv_deposit_pending_almost_filled_auction(
    testenv_almost_filled_auction, accounts, chain
) -> TestEnv:
    """A testenv with auction awaiting deposit transfer with a number of bidders below the maximal number of bidders"""
    time_travel_to_end_of_auction(chain)
    testenv_almost_filled_auction.close_auction(accounts[0])
    testenv_almost_filled_auction.assert_auction_state(AuctionState.DepositPending)
    return testenv_almost_filled_auction


@pytest.fixture(scope="session", params=["ValidatorAuction", "TokenValidatorAuction"])
def testenv_real_price_auction(
    request,
    make_requested_testenv_for_contracts,
    real_price_validator_auction_contract,
    real_price_token_validator_auction_contract,
    auctionnable_token_contract,
) -> TestEnv:

    return make_requested_testenv_for_contracts(
        request=request,
        eth_auction=real_price_validator_auction_contract,
        token_auction=real_price_token_validator_auction_contract,
        token=auctionnable_token_contract,
    )


@pytest.fixture(scope="session")
def make_requested_testenv_for_contracts(web3):
    def make_testenv(*, request, eth_auction, token_auction, token) -> TestEnv:
        if request.param == "ValidatorAuction":
            auction = eth_auction
            token_contract = None
        elif request.param == "TokenValidatorAuction":
            auction = token_auction
            token_contract = token
        else:
            raise ValueError(f"Not handled request param: {request.param}")

        return TestEnv(web3, auction, token_contract)

    return make_testenv


def time_travel_to_end_of_auction(chain):
    chain.time_travel(int(time.time()) + TWO_WEEKS_IN_SECONDS + 10000)
    # It appears that the estimation of whether a transaction will fail is done on the latest block
    # while estimating gas cost for the transaction.
    # If we do not mine a block, the estimation will consider the wrong block time.
    chain.mine_block()


def test_auction_state_deployed(testenv):
    testenv.assert_auction_state(AuctionState.Deployed)


def test_cannot_bid_when_not_started(testenv, accounts):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.bid(accounts[1], TEST_PRICE)


def test_auction_start_deposit_not_init(
    deploy_contract, non_initialized_deposit_locker_contract_session
):
    # TODO: use BaseAuction
    contract = deploy_contract(
        "TestValidatorAuctionFixedPrice",
        constructor_args=(non_initialized_deposit_locker_contract_session.address,),
    )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.startAuction().transact()


def test_auction_start(testenv, accounts, web3):

    testenv.start_auction(accounts[0])

    start_time = web3.eth.getBlock("latest").timestamp

    assert testenv.auction_start_time == start_time
    testenv.assert_auction_state(AuctionState.Started)


def test_auction_start_not_owner(testenv, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv.start_auction(accounts[1])


def test_bidding_not_whitelisted(testenv_started_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.bid(accounts[0], TEST_PRICE)


def test_bidding_bid_below_current_price(testenv_started_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.bid(accounts[1], TEST_PRICE - 1)


def test_bidding(testenv_started_auction: TestEnv, accounts):

    bid_value = 219
    testenv_started_auction.bid(accounts[1], bid_value)

    if testenv_started_auction.use_token:
        # For a token auction, the auction always takes current price as bid
        assert testenv_started_auction.get_bid(accounts[1]) == TEST_PRICE
    else:
        # For an eth auction, the auction takes the full sent message as bid
        assert testenv_started_auction.get_bid(accounts[1]) == bid_value


def test_bidding_too_late(testenv_started_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.bid(accounts[1], TEST_PRICE)


def test_already_bid(testenv_started_auction, accounts):

    testenv_started_auction.bid(accounts[1], TEST_PRICE)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.bid(accounts[1], TEST_PRICE)


def test_auction_failed(testenv_started_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    testenv_started_auction.close_auction()  # accounts[2])
    testenv_started_auction.assert_auction_state(AuctionState.Failed)


def test_bidding_auction_failed(testenv_started_auction, accounts, chain):

    time_travel_to_end_of_auction(chain)
    testenv_started_auction.close_auction(accounts[2])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.bid(accounts[1], TEST_PRICE)


def test_close_auction_too_soon(testenv_started_auction, accounts):

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.close_auction(accounts[2])


@pytest.mark.slow
def test_enough_bidders_ends_auction(testenv_almost_filled_auction: TestEnv, accounts):

    testenv_almost_filled_auction.assert_auction_state(AuctionState.Started)
    testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE)
    testenv_almost_filled_auction.assert_auction_state(AuctionState.DepositPending)


@pytest.mark.slow
def test_end_auction_not_filled(
    testenv_almost_filled_auction: TestEnv, accounts, chain
):

    testenv_almost_filled_auction.assert_auction_state(AuctionState.Started)

    time_travel_to_end_of_auction(chain)

    testenv_almost_filled_auction.close_auction(accounts[1])
    testenv_almost_filled_auction.assert_auction_state(AuctionState.DepositPending)


@pytest.mark.slow
def test_bidding_auction_ended(testenv_almost_filled_auction: TestEnv, accounts):

    testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE)
    testenv_almost_filled_auction.assert_auction_state(AuctionState.DepositPending)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE)


@pytest.mark.slow
def test_send_bids_to_locker(
    testenv_deposit_pending_auction: TestEnv,
    accounts,
    maximal_number_of_auction_participants,
):

    assert testenv_deposit_pending_auction.deposit_locker_balance == 0

    pre_balance = testenv_deposit_pending_auction.auction_balance
    testenv_deposit_pending_auction.deposit_bids(accounts[5])
    post_balance = testenv_deposit_pending_auction.auction_balance

    total_price = (
        maximal_number_of_auction_participants
        * testenv_deposit_pending_auction.lowest_slot_price
    )

    assert post_balance == pre_balance - total_price
    assert testenv_deposit_pending_auction.deposit_locker_balance == total_price
    testenv_deposit_pending_auction.assert_auction_state(AuctionState.Ended)


@pytest.mark.slow
def test_send_bids_to_locker_almost_filled_auction(
    testenv_deposit_pending_almost_filled_auction: TestEnv,
    maximal_number_of_auction_participants,
):

    assert testenv_deposit_pending_almost_filled_auction.deposit_locker_balance == 0

    pre_balance = testenv_deposit_pending_almost_filled_auction.auction_balance
    testenv_deposit_pending_almost_filled_auction.deposit_bids()
    post_balance = testenv_deposit_pending_almost_filled_auction.auction_balance

    total_price = (
        maximal_number_of_auction_participants - 1
    ) * testenv_deposit_pending_almost_filled_auction.lowest_slot_price

    assert post_balance == pre_balance - total_price
    assert (
        testenv_deposit_pending_almost_filled_auction.deposit_locker_balance
        == total_price
    )
    testenv_deposit_pending_almost_filled_auction.assert_auction_state(
        AuctionState.Ended
    )


@pytest.mark.slow
def test_withdraw_overbid(testenv_almost_filled_auction: TestEnv, accounts):

    value_to_bid = 1234

    testenv_almost_filled_auction.bid(accounts[1], value_to_bid)
    testenv_almost_filled_auction.deposit_bids()

    pre_balance = testenv_almost_filled_auction.balance_of(accounts[1])

    testenv_almost_filled_auction.withdraw(accounts[1])
    closing_price = testenv_almost_filled_auction.lowest_slot_price

    post_balance = testenv_almost_filled_auction.balance_of(accounts[1])

    if testenv_almost_filled_auction.use_token:
        # For a token auction, the auction always takes current price as bid
        assert post_balance - pre_balance == TEST_PRICE - closing_price
    else:
        assert post_balance - pre_balance == value_to_bid - closing_price


def test_cannot_withdraw_too_soon(testenv_started_auction: TestEnv, accounts):

    testenv_started_auction.bid(accounts[1], 1234)
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_started_auction.withdraw(accounts[1])


@pytest.mark.slow
def test_cannot_withdraw_twice(testenv_almost_filled_auction: TestEnv, accounts):

    testenv_almost_filled_auction.bid(accounts[1], 1234)
    testenv_almost_filled_auction.deposit_bids()
    testenv_almost_filled_auction.withdraw(accounts[1])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_almost_filled_auction.withdraw(accounts[1])


def test_withdraw_auction_failed(testenv_started_auction: TestEnv, accounts, chain):

    value_to_bid = 1234

    testenv_started_auction.bid(accounts[1], value_to_bid)

    pre_balance = testenv_started_auction.balance_of(accounts[1])

    time_travel_to_end_of_auction(chain)
    testenv_started_auction.close_auction()

    testenv_started_auction.withdraw(accounts[1])

    post_balance = testenv_started_auction.balance_of(accounts[1])

    if testenv_almost_filled_auction.use_token:
        # For a token auction, the auction always takes current price as bid
        assert post_balance - pre_balance == TEST_PRICE
    else:
        assert post_balance - pre_balance == value_to_bid


@pytest.mark.slow
def test_cannot_withdraw_overbid_not_bidder(testenv_almost_filled_auction, accounts):

    testenv_almost_filled_auction.bid(accounts[1], 1234)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_almost_filled_auction.withdraw(accounts[0])


@pytest.mark.slow
def test_withdraw_final_bid_exact_price_failed_auction(
    testenv_started_auction: TestEnv, whitelist, chain
):
    bidder = whitelist[2]

    testenv_started_auction.bid(bidder, TEST_PRICE)

    time_travel_to_end_of_auction(chain)

    testenv_started_auction.close_auction()
    testenv_started_auction.assert_auction_state(AuctionState.Failed)

    pre_balance = testenv_started_auction.balance_of(bidder)

    testenv_started_auction.withdraw(bidder)

    post_balance = testenv_started_auction.balance_of(bidder)
    assert post_balance - pre_balance == TEST_PRICE


def test_event_bid_submitted(testenv_started_auction: TestEnv, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    testenv_started_auction.bid(accounts[1], TEST_PRICE)

    event = testenv_started_auction.auction.events.BidSubmitted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    bid_time = web3.eth.getBlock("latest").timestamp

    assert event["bidder"] == accounts[1]
    assert event["bidValue"] == TEST_PRICE
    assert event["timestamp"] == bid_time


def test_event_auction_started(testenv, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    testenv.start_auction(accounts[0])

    start_time = web3.eth.getBlock("latest").timestamp

    event = testenv.auction.events.AuctionStarted.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["startTime"] == start_time


def test_event_auction_deployed(
    testenv_real_price_auction,
    minimal_number_of_auction_participants,
    maximal_number_of_auction_participants,
):
    event_args = testenv_real_price_auction.auction.events.AuctionDeployed.createFilter(
        fromBlock=0
    ).get_all_entries()[0]["args"]

    assert event_args["startPrice"] == AUCTION_START_PRICE
    assert event_args["auctionDurationInDays"] == AUCTION_DURATION_IN_DAYS
    assert (
        event_args["minimalNumberOfParticipants"]
        == minimal_number_of_auction_participants
    )
    assert (
        event_args["maximalNumberOfParticipants"]
        == maximal_number_of_auction_participants
    )


def test_event_auction_failed(testenv_started_auction: TestEnv, accounts, chain, web3):

    testenv_started_auction.bid(accounts[1], TEST_PRICE)

    time_travel_to_end_of_auction(chain)

    latest_block_number = web3.eth.blockNumber

    testenv_started_auction.close_auction()

    event = testenv_started_auction.auction.events.AuctionFailed.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["closeTime"] == testenv_started_auction.close_time
    assert event["numberOfBidders"] == 1


@pytest.mark.slow
def test_event_deposit_pending(testenv_almost_filled_auction, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE * 2 + 1)

    close_time = web3.eth.getBlock("latest").timestamp

    event = testenv_almost_filled_auction.auction.events.AuctionDepositPending.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[
        0
    ][
        "args"
    ]

    assert event["closeTime"] == close_time
    assert event["lowestSlotPrice"] == TEST_PRICE


@pytest.mark.slow
def test_event_auction_ended(testenv_almost_filled_auction: TestEnv, accounts, web3):

    latest_block_number = web3.eth.blockNumber

    testenv_almost_filled_auction.bid(accounts[1], TEST_PRICE * 2 + 1)
    close_time = web3.eth.getBlock("latest").timestamp

    testenv_almost_filled_auction.deposit_bids()

    event = testenv_almost_filled_auction.auction.events.AuctionEnded.createFilter(
        fromBlock=latest_block_number
    ).get_all_entries()[0]["args"]

    assert event["closeTime"] == close_time
    assert event["lowestSlotPrice"] == TEST_PRICE


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
    testenv_real_price_auction: TestEnv, hours_since_start, python_price
):

    testenv_real_price_auction.start_auction()

    seconds_since_start = ONE_HOUR_IN_SECONDS * hours_since_start
    blockchain_price = testenv_real_price_auction.get_price_at_elapsed_time(
        seconds_since_start
    )

    assert blockchain_price == pytest.approx(python_price, abs=1e16)


@pytest.mark.parametrize(
    "hours_since_start, price_min, price_max",
    [
        (0, AUCTION_START_PRICE, AUCTION_START_PRICE),
        (AUCTION_DURATION_IN_DAYS * 24 // 2, 3 * ETH_IN_WEI, 4 * ETH_IN_WEI),
        (AUCTION_DURATION_IN_DAYS * 24, 1 * ETH_IN_WEI, 2 * ETH_IN_WEI),
    ],
)
def test_price(testenv_real_price_auction, hours_since_start, price_min, price_max):

    testenv_real_price_auction.start_auction()

    seconds_since_start = ONE_HOUR_IN_SECONDS * hours_since_start

    blockchain_price = testenv_real_price_auction.get_price_at_elapsed_time(
        seconds_since_start
    )

    assert price_min <= blockchain_price <= price_max


def test_bid_real_price_auction(
    testenv_real_price_auction: TestEnv, accounts, chain, web3
):

    testenv_real_price_auction.start_auction()
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # Need to mine a block after time travel to make the call consider the new block time.
    chain.mine_block()

    price = testenv_real_price_auction.current_price

    testenv_real_price_auction.bid(accounts[1], price)


def test_current_price_auction_not_started_fails(testenv_real_price_auction):
    """The current price is calculated based on start time
    The function must thus not be called when auction is not started"""

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_real_price_auction.current_price


def test_too_low_bid_fails_real_price_auction(
    testenv_real_price_auction: TestEnv, accounts, chain, web3
):

    testenv_real_price_auction.start_auction()
    start_time = web3.eth.getBlock("latest").timestamp

    chain.time_travel(start_time + 123456)
    # Need to mine a block after time travel to make the call consider the new block time.
    chain.mine_block()

    price_before_mining = testenv_real_price_auction.current_price
    chain.mine_block()
    price_after_mining = testenv_real_price_auction.current_price

    price_variation_on_block = price_before_mining - price_after_mining

    # If we use a token auction, we need to double the price variation on block
    # Because a block will be mined when approving the tokens to bid on the auction
    if testenv_real_price_auction.token:
        too_low_price = (
            testenv_real_price_auction.current_price - 2 * price_variation_on_block
        )
    else:
        too_low_price = (
            testenv_real_price_auction.current_price - price_variation_on_block
        )

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        testenv_real_price_auction.bid(accounts[1], too_low_price)
        chain.mine_block()
