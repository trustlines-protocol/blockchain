import pytest

from gevent import monkey

monkey.patch_all(thread=False)  # noqa: E702

from gevent import Greenlet
from time import sleep

from bridge.event_fetcher import EventFetcher


@pytest.fixture
def transfer_event_name():
    """Name of event to fetch from the token ABI"""
    return "Transfer"


@pytest.fixture
def transfer_event_argument_filter(foreign_bridge_contract):
    """Argument values to filter the token transfer event"""
    return {"to": foreign_bridge_contract.address}


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
    transfer_event_name,
    transfer_event_argument_filter,
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
        "event_name": transfer_event_name,
        "event_argument_filter": transfer_event_argument_filter,
        "event_queue": transfer_event_queue,
        "max_reorg_depth": foreign_chain_max_reorg_depth,
        "start_block_number": foreign_chain_event_fetch_start_block_number,
    }


@pytest.fixture
def transfer_event_fetcher(transfer_event_fetcher_init_kwargs):
    """Default test instance of the event filter for the token transfer event"""
    return EventFetcher(**transfer_event_fetcher_init_kwargs)


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
    transfer_event_fetcher_init_kwargs
):
    with pytest.raises(ValueError):
        return EventFetcher(
            **{**transfer_event_fetcher_init_kwargs, "event_fetch_limit": -1}
        )


def test_instantiate_event_fetcher_with_negative_max_reorg_depth(
    transfer_event_fetcher_init_kwargs
):
    with pytest.raises(ValueError):
        return EventFetcher(
            **{**transfer_event_fetcher_init_kwargs, "max_reorg_depth": -1}
        )


def test_instantiate_event_fetcher_with_negative_start_block_number(
    transfer_event_fetcher_init_kwargs
):
    with pytest.raises(ValueError):
        return EventFetcher(
            **{**transfer_event_fetcher_init_kwargs, "start_block_number": -1}
        )


def test_fetch_events_in_range(
    transfer_event_fetcher,
    w3_foreign,
    transfer_event_name,
    transfer_event_argument_filter,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)

    assert transfer_event_queue.qsize() == 1

    event = transfer_event_queue.get()

    assert event["event"] == transfer_event_name

    for argument_name, argument_value in transfer_event_argument_filter.items():
        assert event.args[argument_name] == argument_value


def test_fetch_events_in_range_ignore_not_matching_arguments(
    transfer_event_fetcher, transfer_event_queue, transfer_tokens_to, w3_foreign
):
    assert transfer_event_queue.empty()

    transfer_tokens_to("0xbB1046b0Fe450aA48DEafF6Fa474AdBf972840dD")
    transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)

    assert transfer_event_queue.empty()


def test_fetch_events_in_range_negative_from_number(transfer_event_fetcher):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events_in_range(-1, 1)


def test_fetch_events_in_range_to_high_to_number(transfer_event_fetcher, w3_foreign):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber + 1)


def test_fetch_events_in_range_negative_range(transfer_event_fetcher):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events_in_range(1, 0)


def test_fetch_events_not_seen_ignore_reorg_depth_blocks(
    transfer_event_fetcher,
    w3_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()

    assert w3_foreign.eth.blockNumber < foreign_chain_max_reorg_depth

    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.empty()


def test_fetch_events_not_seen(
    transfer_event_fetcher,
    tester_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == 1


def test_fetch_events_not_seen_handle_event_limit_exact_multiplicate(
    transfer_event_fetcher_init_kwargs,
    tester_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    reduced_event_fetch_limit = 25
    transfer_event_fetcher = EventFetcher(
        **{
            **transfer_event_fetcher_init_kwargs,
            "event_fetch_limit": reduced_event_fetch_limit,
        }
    )
    transfer_count = reduced_event_fetch_limit * 2

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == transfer_count


def test_fetch_events_not_seen_handle_event_limit_not_exact_multiplicate(
    transfer_event_fetcher_init_kwargs,
    tester_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    reduced_event_fetch_limit = 25
    transfer_event_fetcher = EventFetcher(
        **{
            **transfer_event_fetcher_init_kwargs,
            "event_fetch_limit": reduced_event_fetch_limit,
        }
    )
    transfer_count = reduced_event_fetch_limit + 1

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == transfer_count


def test_fetch_events_not_seen_apply_start_block_number(
    transfer_event_fetcher,
    w3_foreign,
    tester_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_event_fetcher.last_fetched_block_number = w3_foreign.eth.blockNumber
    transfer_tokens_to_foreign_bridge()
    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == 1


def test_fetch_events_continuously(
    transfer_event_fetcher_init_kwargs,
    tester_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
):
    assert transfer_event_queue.empty()

    poll_time = 1
    transfer_event_fetcher = EventFetcher(
        **{**transfer_event_fetcher_init_kwargs, "max_reorg_depth": 0}
    )

    try:
        greenlet = Greenlet.spawn(transfer_event_fetcher.fetch_events, poll_time)
        transfer_tokens_to_foreign_bridge()
        sleep(poll_time + 1)

        assert transfer_event_queue.qsize() == 1

        transfer_tokens_to_foreign_bridge()
        transfer_tokens_to_foreign_bridge()
        sleep(poll_time + 1)

        assert transfer_event_queue.qsize() == 3

    finally:
        greenlet.kill()


def test_fetch_events_negative_poll_interval(
    transfer_event_fetcher, transfer_event_queue, transfer_tokens_to_foreign_bridge
):
    with pytest.raises(ValueError):
        transfer_event_fetcher.fetch_events(poll_interval=-1)
