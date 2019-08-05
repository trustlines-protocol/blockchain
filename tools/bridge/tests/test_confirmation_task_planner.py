from itertools import count

import pytest

from eth_utils import int_to_big_endian

from bridge.confirmation_task_planner import (
    TransferHashRecorder,
    ConfirmationTaskPlanner,
)


@pytest.fixture
def recorder():
    """A transfer hash recorder"""
    return TransferHashRecorder()


@pytest.fixture
def transfer_hashes():
    """A generator that produces an infinite, non-repeatable sequence of hashes."""
    return (int_to_big_endian(counter).rjust(32, b"\x00") for counter in count())


@pytest.fixture
def home_look_ahead():
    """The home look ahead time of the confirmation task planner."""
    return 5


@pytest.fixture
def history_length():
    """The history length of the confirmation task planner."""
    return 60


@pytest.fixture
def planner(home_look_ahead, history_length):
    """A confirmation task planner."""
    return ConfirmationTaskPlanner(
        home_look_ahead=home_look_ahead, history_length=history_length
    )


def test_recorder_records_hashes(recorder, transfer_hashes):
    transfer_hash = next(transfer_hashes)
    assert not recorder.transfer_hash_exists(transfer_hash)
    recorder.record_transfer_hash(10, transfer_hash)
    assert recorder.transfer_hash_exists(transfer_hash)


def test_recorder_updates_time(recorder, transfer_hashes):
    assert recorder.current_timestamp == 0
    recorder.record_transfer_hash(10, next(transfer_hashes))
    assert recorder.current_timestamp == 10
    recorder.record_transfer_hash(10, None)
    assert recorder.current_timestamp == 10
    recorder.record_transfer_hash(15, next(transfer_hashes))
    assert recorder.current_timestamp == 15


def test_recorder_prevents_out_of_order_events(recorder, transfer_hashes):
    recorder.record_transfer_hash(10, next(transfer_hashes))
    with pytest.raises(ValueError):
        recorder.record_transfer_hash(9, next(transfer_hashes))


def test_recorder_forgets_hashes(recorder, transfer_hashes):
    transfer_hash = next(transfer_hashes)
    recorder.record_transfer_hash(10, transfer_hash)
    recorder.forget_transfer_hash(transfer_hash)
    assert not recorder.transfer_hash_exists(transfer_hash)
    assert len(recorder.get_transfer_hashes(10, 10)) == 0
    assert recorder.current_timestamp == 10


def test_recorder_gets_hashes_in_time_interval(recorder, transfer_hashes):
    transfer_hash_1 = next(transfer_hashes)
    transfer_hash_2 = next(transfer_hashes)
    transfer_hash_3 = next(transfer_hashes)
    recorder.record_transfer_hash(10, transfer_hash_1)
    recorder.record_transfer_hash(12, transfer_hash_2)
    recorder.record_transfer_hash(14, transfer_hash_3)
    assert recorder.get_transfer_hashes(10, 12) == [transfer_hash_1, transfer_hash_2]


def test_planner_plans_transfers(planner, transfer_hashes, home_look_ahead):
    assert planner.get_next_transfer_hashes() == []

    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash("Transfer", 10, transfer_hash)
    planner.apply_transfer_hash("Confirmation", 10 + home_look_ahead, None)
    planner.apply_transfer_hash("Completion", 10 + home_look_ahead, None)
    assert planner.get_next_transfer_hashes() == [transfer_hash]
    assert planner.get_next_transfer_hashes() == []


def test_planner_ignores_transfers_not_in_look_ahead(
    planner, transfer_hashes, home_look_ahead
):
    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash("Transfer", 10, transfer_hash)
    planner.apply_transfer_hash("Confirmation", 10 + home_look_ahead - 1, None)
    assert planner.get_next_transfer_hashes() == []


def test_planner_clears_historic_transfers(
    planner, transfer_hashes, home_look_ahead, history_length
):
    forgot_transfer_hash = next(transfer_hashes)
    remembered_transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash("Transfer", 10, forgot_transfer_hash)
    planner.apply_transfer_hash(
        "Transfer", 10 + history_length + 1, remembered_transfer_hash
    )
    planner.apply_transfer_hash(
        "Confirmation", 10 + history_length + 1 + home_look_ahead, None
    )
    planner.apply_transfer_hash(
        "Completion", 10 + history_length + 1 + home_look_ahead, None
    )
    planner.clear_history()
    assert planner.get_next_transfer_hashes() == [remembered_transfer_hash]


def test_planner_clears_fully_processed_transfers(
    planner, transfer_hashes, home_look_ahead
):
    transfer_hash = next(transfer_hashes)
    planner.apply_transfer_hash("Transfer", 10, transfer_hash)
    planner.apply_transfer_hash("Confirmation", 10 + home_look_ahead, transfer_hash)
    planner.apply_transfer_hash("Completion", 10 + home_look_ahead, transfer_hash)
    planner.clear_history()
    assert planner.get_next_transfer_hashes() == []
