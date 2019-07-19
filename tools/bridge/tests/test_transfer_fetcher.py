import pytest

from web3 import Web3

from bridge.transfer_fetcher import TransferFetcher


@pytest.fixture
def foreign_chain_max_reorg_depth():
    return 10


@pytest.fixture
def transfer_event_fetch_limit():
    return 25


@pytest.fixture
def transfer_fetcher(
    token_transfer_event_queue,
    w3_foreign,
    token_contract,
    foreign_bridge_contract,
    foreign_chain_max_reorg_depth,
    transfer_event_fetch_limit,
):
    return TransferFetcher(
        queue=token_transfer_event_queue,
        w3_foreign=w3_foreign,
        token_contract_address=token_contract.address,
        foreign_bridge_contract_address=foreign_bridge_contract.address,
        foreign_chain_max_reorg_depth=foreign_chain_max_reorg_depth,
        transfer_event_fetch_limit=transfer_event_fetch_limit,
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


def test_instantiate_transfer_fetcher_with_non_existing_token_contract(
    token_transfer_event_queue,
    w3_foreign,
    foreign_bridge_contract,
    foreign_chain_max_reorg_depth,
    transfer_event_fetch_limit,
):
    with pytest.raises(ValueError):
        TransferFetcher(
            queue=token_transfer_event_queue,
            w3_foreign=w3_foreign,
            token_contract_address="0x0000000000000000000000000000000000000000",
            foreign_bridge_contract_address=foreign_bridge_contract.address,
            foreign_chain_max_reorg_depth=foreign_chain_max_reorg_depth,
            transfer_event_fetch_limit=transfer_event_fetch_limit,
        )


def test_instantiate_transfer_fetcher_with_incorrect_token_contract(
    token_transfer_event_queue,
    w3_foreign,
    foreign_bridge_contract,
    transfer_event_fetch_limit,
):
    with pytest.raises(ValueError):
        TransferFetcher(
            queue=token_transfer_event_queue,
            w3_foreign=w3_foreign,
            token_contract_address=foreign_bridge_contract.address,
            foreign_bridge_contract_address=foreign_bridge_contract.address,
            foreign_chain_max_reorg_depth=foreign_chain_max_reorg_depth,
            transfer_event_fetch_limit=transfer_event_fetch_limit,
        )


def test_instantiate_transfer_fetcher_with_non_existing_foreign_bridge_contract(
    token_transfer_event_queue,
    w3_foreign,
    token_contract,
    foreign_chain_max_reorg_depth,
    transfer_event_fetch_limit,
):
    with pytest.raises(ValueError):
        TransferFetcher(
            queue=token_transfer_event_queue,
            w3_foreign=w3_foreign,
            token_contract_address=token_contract.address,
            foreign_bridge_contract_address="0x0000000000000000000000000000000000000000",
            foreign_chain_max_reorg_depth=foreign_chain_max_reorg_depth,
            transfer_event_fetch_limit=transfer_event_fetch_limit,
        )


def test_fetch_token_transfer_events_in_range(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    w3_foreign,
    premint_token_address,
):
    assert token_transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_fetcher._fetch_token_transfer_events_in_range(
        0, w3_foreign.eth.blockNumber
    )

    assert token_transfer_event_queue.qsize() == 1
    assert token_transfer_event_queue.get()["topics"][0] == Web3.keccak(
        text="Transfer(address,address,uint256)"
    )


def test_fetch_token_transfer_events_in_range_fix_invalid_bounds(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    w3_foreign,
):
    assert token_transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    transfer_fetcher._fetch_token_transfer_events_in_range(
        -1, w3_foreign.eth.blockNumber + 1
    )

    assert token_transfer_event_queue.qsize() == 1


def test_fetch_token_transfer_events_in_range_ignore_transfers_not_to_bridge(
    transfer_fetcher, token_transfer_event_queue, transfer_tokens_to, w3_foreign
):
    assert token_transfer_event_queue.empty()

    transfer_tokens_to("0xbB1046b0Fe450aA48DEafF6Fa474AdBf972840dD")
    transfer_fetcher._fetch_token_transfer_events_in_range(
        0, w3_foreign.eth.blockNumber
    )

    assert token_transfer_event_queue.empty()


def test_fetch_token_transfer_events_in_range_invalid_range(
    transfer_fetcher, token_transfer_event_queue, transfer_tokens_to, w3_foreign
):
    with pytest.raises(AssertionError):
        transfer_fetcher._fetch_token_transfer_events_in_range(1, 0)


def test_fetch_token_transfer_events_not_seen_ignore_reorg_depth_blocks(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    w3_foreign,
    foreign_chain_max_reorg_depth,
):
    assert token_transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()

    assert w3_foreign.eth.blockNumber < foreign_chain_max_reorg_depth

    transfer_fetcher._fetch_token_transfer_events_not_seen()

    assert token_transfer_event_queue.empty()


def test_fetch_token_transfer_events_not_seen(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    tester_foreign,
    foreign_chain_max_reorg_depth,
):
    assert token_transfer_event_queue.empty()

    transfer_tokens_to_foreign_bridge()
    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_fetcher._fetch_token_transfer_events_not_seen()

    assert token_transfer_event_queue.qsize() == 1


def test_fetch_token_transfer_events_not_seen_handle_log_limit_exact_multiplicate(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    tester_foreign,
    foreign_chain_max_reorg_depth,
    transfer_event_fetch_limit,
    w3_foreign,
):
    assert token_transfer_event_queue.empty()

    transfer_count = transfer_event_fetch_limit * 2

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_fetcher._fetch_token_transfer_events_not_seen()

    assert token_transfer_event_queue.qsize() == transfer_count


def test_fetch_token_transfer_events_not_seen_handle_log_limit_not_exact_multiplicate(
    transfer_fetcher,
    token_transfer_event_queue,
    transfer_tokens_to_foreign_bridge,
    tester_foreign,
    foreign_chain_max_reorg_depth,
    transfer_event_fetch_limit,
):
    assert token_transfer_event_queue.empty()

    transfer_count = transfer_event_fetch_limit + 1

    for i in range(transfer_count):
        transfer_tokens_to_foreign_bridge()

    tester_foreign.mine_blocks(foreign_chain_max_reorg_depth)
    transfer_fetcher._fetch_token_transfer_events_not_seen()

    assert token_transfer_event_queue.qsize() == transfer_count


# TODO: test worker when async framework integrated
