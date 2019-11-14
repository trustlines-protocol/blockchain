from typing import List

import gevent
import pytest

from bridge.constants import TRANSFER_EVENT_NAME
from bridge.event_fetcher import EventFetcher, FetcherReachedHeadEvent
from bridge.events import ChainRole


def fetch_all_events(fetcher: EventFetcher) -> List:
    result: List = []
    while 1:
        events = fetcher.fetch_some_events()
        if not events:
            return result
        result.extend(events)


@pytest.fixture
def transfer_event_filter_definition(foreign_bridge_contract):
    """Filter definition to fetch only Transfer events to the token transfer event"""
    return {TRANSFER_EVENT_NAME: {"to": foreign_bridge_contract.address}}


@pytest.fixture
def foreign_chain_max_reorg_depth():
    """Number of confirmed blocks after finality is assumed on the foreign chain"""
    return 10


@pytest.fixture
def foreign_chain_event_fetch_start_block_number():
    """Block number from where to start fetching event on the foreign chain"""
    return 0


@pytest.fixture
def transfer_event_fetcher_init_kwargs(
    w3_foreign,
    token_contract,
    transfer_event_filter_definition,
    transfer_event_queue,
    foreign_chain_max_reorg_depth,
    foreign_chain_event_fetch_start_block_number,
):
    """Dictionary with the default initialization argument for the transfer event fetcher

    Meant to be reused on instantiation and partially overwritten for the specific use case.
    """

    return {
        "web3": w3_foreign,
        "contract": token_contract,
        "filter_definition": transfer_event_filter_definition,
        "event_queue": transfer_event_queue,
        "max_reorg_depth": foreign_chain_max_reorg_depth,
        "start_block_number": foreign_chain_event_fetch_start_block_number,
        "chain_role": ChainRole.home,
    }


@pytest.fixture
def make_transfer_event_fetcher(transfer_event_fetcher_init_kwargs):
    """returns a function that can be used to create an EventFetcher that fetches Transfer events

keyword arguments passed to this function overwrite the defaults from
the transfer_event_fetcher_init_kwargs fixture
    """

    def make_fetcher(**kw):
        return EventFetcher(**{**transfer_event_fetcher_init_kwargs, **kw})

    return make_fetcher


@pytest.fixture
def transfer_event_fetcher(make_transfer_event_fetcher):
    """Default test instance of the event filter for the token transfer event"""
    return make_transfer_event_fetcher()


@pytest.fixture
def transfer_tokens_to(token_contract, premint_token_address):
    """Function to transfer token to an address

    The amount is a fixed value of one.
    This will emit the Transfer event of the token contract.
    """

    def transfer(receiver):
        token_contract.functions.transfer(receiver, 1).transact(
            {"from": premint_token_address}
        )

    return transfer


@pytest.fixture
def transfer_tokens_to_foreign_bridge(foreign_bridge_contract, transfer_tokens_to):
    """Function to transfer token to the foreign bridge contract

    The emitted token transfer event matches the argument filter of the event
    fetcher.
    """

    def transfer():
        transfer_tokens_to(foreign_bridge_contract.address)

    return transfer


def test_instantiate_event_fetcher_with_negative_event_fetch_limit(
    make_transfer_event_fetcher
):
    with pytest.raises(ValueError):
        make_transfer_event_fetcher(event_fetch_limit=-1)


def test_instantiate_event_fetcher_with_negative_max_reorg_depth(
    make_transfer_event_fetcher
):
    with pytest.raises(ValueError):
        make_transfer_event_fetcher(max_reorg_depth=-1)


def test_instantiate_event_fetcher_with_negative_start_block_number(
    make_transfer_event_fetcher
):
    with pytest.raises(ValueError):
        make_transfer_event_fetcher(start_block_number=-1)


def test_fetch_events_in_range(
    transfer_event_fetcher,
    w3_foreign,
    transfer_event_filter_definition,
    transfer_tokens_to_foreign_bridge,
):
    transfer_tokens_to_foreign_bridge()
    events = transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)

    assert len(events) == 1

    event = events[0]

    assert event["event"] == TRANSFER_EVENT_NAME

    transfer_arguments = transfer_event_filter_definition[TRANSFER_EVENT_NAME]
    for argument_name, argument_value in transfer_arguments.items():
        assert event.args[argument_name] == argument_value


def test_fetch_events_in_range_ignore_not_matching_arguments(
    transfer_event_fetcher, transfer_tokens_to, w3_foreign
):
    transfer_tokens_to("0xbB1046b0Fe450aA48DEafF6Fa474AdBf972840dD")
    events = transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)
    assert len(events) == 0


def test_fetch_events_in_range_negative_from_number(transfer_event_fetcher):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events_in_range(-1, 1)


def test_fetch_events_in_range_negative_range(transfer_event_fetcher):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events_in_range(1, 0)


def test_fetch_events_ignore_last_reorg_depth_blocks(
    transfer_event_fetcher,
    w3_foreign,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    transfer_tokens_to_foreign_bridge()

    assert w3_foreign.eth.blockNumber < foreign_chain_max_reorg_depth
    events = fetch_all_events(transfer_event_fetcher)
    assert len(events) == 0


def test_fetch_some_events(
    transfer_event_fetcher,
    tester_foreign,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    transfer_tokens_to_foreign_bridge()
    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    events = fetch_all_events(transfer_event_fetcher)
    assert len(events) == 1


@pytest.mark.parametrize("transfer_count", [0, 7, 12, 24, 25, 26, 49, 50, 51])
def test_fetch_some_events_with_different_transfer_counts(
    make_transfer_event_fetcher,
    tester_foreign,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
    transfer_count,
):
    reduced_event_fetch_limit = 25
    transfer_event_fetcher = make_transfer_event_fetcher(
        event_fetch_limit=reduced_event_fetch_limit
    )

    for _ in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    events = fetch_all_events(transfer_event_fetcher)
    assert len(events) == transfer_count


def test_fetch_events_with_start_block_number(
    w3_foreign,
    tester_foreign,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
    make_transfer_event_fetcher,
):

    transfer_tokens_to_foreign_bridge()
    event_block_number = w3_foreign.eth.blockNumber
    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)

    events = fetch_all_events(
        make_transfer_event_fetcher(start_block_number=event_block_number)
    )
    assert len(events) == 1

    events2 = fetch_all_events(
        make_transfer_event_fetcher(start_block_number=event_block_number + 1)
    )
    assert len(events2) == 0


def test_fetch_event_synthetic_sync_event(
    make_transfer_event_fetcher,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    spawn,
):
    assert transfer_event_queue.empty()

    poll_time = 0.1
    transfer_event_fetcher = make_transfer_event_fetcher(max_reorg_depth=0)
    spawn(transfer_event_fetcher.fetch_events, poll_time)

    with gevent.Timeout(poll_time + 0.05):
        assert isinstance(transfer_event_queue.get(), FetcherReachedHeadEvent)


def test_fetch_events_continuously(
    make_transfer_event_fetcher,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    spawn,
):
    assert transfer_event_queue.empty()

    poll_time = 0.1
    transfer_event_fetcher = make_transfer_event_fetcher(max_reorg_depth=0)

    spawn(transfer_event_fetcher.fetch_events, poll_time)
    transfer_tokens_to_foreign_bridge()
    with gevent.Timeout(poll_time + 0.05):
        transfer_event_queue.get()

    transfer_tokens_to_foreign_bridge()
    transfer_tokens_to_foreign_bridge()
    with gevent.Timeout(poll_time + 0.05):
        transfer_event_queue.get()
        transfer_event_queue.get()


def test_fetch_events_negative_poll_interval(transfer_event_fetcher):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events(poll_interval=-1)


def test_fetch_multiple_events(
    make_transfer_event_fetcher,
    token_contract,
    premint_token_address,
    tester_foreign,
    foreign_chain_max_reorg_depth,
):
    transfer_and_approval_fetcher = make_transfer_event_fetcher(
        filter_definition={"Transfer": {}, "Approval": {}}
    )

    token_contract.functions.transfer(premint_token_address, 1).transact(
        {"from": premint_token_address}
    )
    token_contract.functions.approve(premint_token_address, 1).transact(
        {"from": premint_token_address}
    )
    token_contract.functions.approve(premint_token_address, 0).transact(
        {"from": premint_token_address}
    )
    token_contract.functions.transfer(premint_token_address, 1).transact(
        {"from": premint_token_address}
    )

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    events = fetch_all_events(transfer_and_approval_fetcher)[
        -4:
    ]  # there might be earlier events we don't care about
    event_names = [event.event for event in events]
    assert event_names == ["Transfer", "Approval", "Approval", "Transfer"]
