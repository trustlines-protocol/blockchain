import pytest

from web3 import Web3

from bridge.event_fetcher import EventFetcher


@pytest.fixture
def transfer_event_signature_hash():
    return Web3.keccak(text="Transfer(address,address,uint256)")


@pytest.fixture
def transfer_event_argument_filter(foreign_bridge_contract):
    return [None, f"0x000000000000000000000000{foreign_bridge_contract.address[2:]}"]


@pytest.fixture
def foreign_chain_max_reorg_depth():
    return 10


@pytest.fixture
def event_fetch_limit():
    return 25


@pytest.fixture
def transfer_event_fetcher(
    w3_foreign,
    token_contract,
    transfer_event_signature_hash,
    transfer_event_argument_filter,
    transfer_event_queue,
    event_fetch_limit,
    foreign_chain_max_reorg_depth,
):
    return EventFetcher(
        web3=w3_foreign,
        contract_address=token_contract.address,
        event_signature_hash=transfer_event_signature_hash,
        event_argument_filter=transfer_event_argument_filter,
        event_fetch_limit=event_fetch_limit,
        event_queue=transfer_event_queue,
        max_reorg_depth=foreign_chain_max_reorg_depth,
    )


@pytest.fixture
def transfer_tokens_to(token_contract, premint_token_address):
    def transfer(receiver):
        token_contract.functions.transfer(receiver, 1).transact(
            {"from": premint_token_address}
        )

    return transfer


@pytest.fixture
def transfer_tokens_to_foreign_bridge(foreign_bridge_contract, transfer_tokens_to):
    def transfer():
        transfer_tokens_to(foreign_bridge_contract.address)

    return transfer


def test_instantiate_event_fetcher_with_non_existing_contract(
    w3_foreign,
    transfer_event_signature_hash,
    transfer_event_argument_filter,
    event_fetch_limit,
    transfer_event_queue,
    foreign_chain_max_reorg_depth,
):
    with pytest.raises(ValueError):
        return EventFetcher(
            web3=w3_foreign,
            contract_address="0x0000000000000000000000000000000000000000",
            event_signature_hash=transfer_event_signature_hash,
            event_argument_filter=transfer_event_argument_filter,
            event_fetch_limit=event_fetch_limit,
            event_queue=transfer_event_queue,
            max_reorg_depth=foreign_chain_max_reorg_depth,
        )


def test_instantiate_event_fetcher_with_not_existing_event_signature(
    w3_foreign,
    token_contract,
    transfer_event_argument_filter,
    event_fetch_limit,
    transfer_event_queue,
    foreign_chain_max_reorg_depth,
):
    with pytest.raises(ValueError):
        return EventFetcher(
            web3=w3_foreign,
            contract_address=token_contract.address,
            event_signature_hash=Web3.keccak(text="NonExistingEvent(bytes)"),
            event_argument_filter=transfer_event_argument_filter,
            event_fetch_limit=event_fetch_limit,
            event_queue=transfer_event_queue,
            max_reorg_depth=foreign_chain_max_reorg_depth,
        )


def test_instantiate_event_fetcher_with_negative_event_fetch_limit(
    w3_foreign,
    token_contract,
    transfer_event_signature_hash,
    transfer_event_argument_filter,
    transfer_event_queue,
    foreign_chain_max_reorg_depth,
):
    with pytest.raises(AssertionError):
        return EventFetcher(
            web3=w3_foreign,
            contract_address=token_contract.address,
            event_signature_hash=transfer_event_signature_hash,
            event_argument_filter=transfer_event_argument_filter,
            event_fetch_limit=-1,
            event_queue=transfer_event_queue,
            max_reorg_depth=foreign_chain_max_reorg_depth,
        )


def test_instantiate_event_fetcher_with_negative_max_reorg_depth(
    w3_foreign,
    token_contract,
    transfer_event_signature_hash,
    transfer_event_argument_filter,
    event_fetch_limit,
    transfer_event_queue,
    foreign_chain_max_reorg_depth,
):
    with pytest.raises(AssertionError):
        return EventFetcher(
            web3=w3_foreign,
            contract_address=token_contract.address,
            event_signature_hash=transfer_event_signature_hash,
            event_argument_filter=transfer_event_argument_filter,
            event_fetch_limit=event_fetch_limit,
            event_queue=transfer_event_queue,
            max_reorg_depth=-1,
        )


def test_fetch_events_in_range(
    transfer_event_fetcher,
    w3_foreign,
    transfer_event_signature_hash,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)

    assert transfer_event_queue.qsize() == 1
    assert transfer_event_queue.get()["topics"][0] == transfer_event_signature_hash


def test_fetch_events_in_range_fix_invalid_bounds(
    transfer_event_fetcher,
    w3_foreign,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
):
    assert transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_event_fetcher.fetch_events_in_range(-1, w3_foreign.eth.blockNumber + 1)

    assert transfer_event_queue.qsize() == 1


def test_fetch_events_in_range_apply_argument_filter(
    transfer_event_fetcher, transfer_event_queue, transfer_tokens_to, w3_foreign
):
    assert transfer_event_queue.empty()

    transfer_tokens_to("0xbB1046b0Fe450aA48DEafF6Fa474AdBf972840dD")
    transfer_event_fetcher.fetch_events_in_range(0, w3_foreign.eth.blockNumber)

    assert transfer_event_queue.empty()


def test_fetch_events_in_range_invalid_range(transfer_event_fetcher):
    with pytest.raises(AssertionError):
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


def test_fetch_events_not_seen_handle_log_limit_exact_multiplicate(
    transfer_event_fetcher,
    w3_foreign,
    tester_foreign,
    event_fetch_limit,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    transfer_count = event_fetch_limit * 2

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == transfer_count


def test_fetch_events_not_seen_handle_log_limit_not_exact_multiplicate(
    transfer_event_fetcher,
    tester_foreign,
    event_fetch_limit,
    transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    foreign_chain_max_reorg_depth,
):
    assert transfer_event_queue.empty()

    transfer_count = event_fetch_limit + 1

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_event_fetcher.fetch_events_not_seen()

    assert transfer_event_queue.qsize() == transfer_count


# TODO: test worker when async framework integrated
