import gevent
import pytest
from gevent.queue import Queue

from bridge.events import BalanceCheck
from bridge.validator_balance_watcher import ValidatorBalanceWatcher


@pytest.fixture
def poll_interval():
    return 0.1


@pytest.fixture
def control_queue():
    return Queue()


@pytest.fixture
def address(accounts):
    return accounts[0]


@pytest.fixture
def another_address(accounts):
    return accounts[1]


@pytest.fixture
def watcher(w3_home, address, poll_interval, control_queue, spawn):
    watcher = ValidatorBalanceWatcher(
        w3=w3_home,
        validator_address=address,
        poll_interval=poll_interval,
        control_queue=control_queue,
    )
    spawn(watcher.run)
    yield watcher


def test_balance_watcher(
    w3_home, watcher, poll_interval, address, another_address, control_queue
):
    initial_balance = w3_home.eth.getBalance(address)
    gevent.sleep(poll_interval * 2.1)

    w3_home.eth.sendTransaction(
        {"from": address, "value": 1, "gasPrice": 0, "to": another_address}
    )
    new_balance = initial_balance - 1
    gevent.sleep(poll_interval * 2.1)

    events = []
    while not control_queue.empty():
        events.append(control_queue.get_nowait())

    assert len(events) >= 4
    assert all(isinstance(event, BalanceCheck) for event in events)
    assert events[:2] == [BalanceCheck(initial_balance)] * 2
    assert events[-2:] == [BalanceCheck(new_balance)] * 2
