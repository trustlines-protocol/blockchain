from unittest.mock import Mock

import gevent
from eth_utils import to_canonical_address
from gevent import Timeout
from gevent.queue import Queue

from bridge.events import IsValidatorCheck
from bridge.validator_status_watcher import ValidatorStatusWatcher


def test_watcher_checks_initial_validator_status_correctly(
    validator_proxy_with_validators, validator_address, spawn
):
    control_queue = Queue()
    stop_callback = Mock()
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(validator_address),
        poll_interval=1,
        control_queue=control_queue,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(True)
    stop_callback.assert_not_called()


def test_watcher_checks_initial_non_validator_status_correctly(
    validator_proxy_with_validators, non_validator_address, spawn
):
    control_queue = Queue()
    stop_callback = Mock()
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(non_validator_address),
        poll_interval=1,
        control_queue=control_queue,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(False)
    stop_callback.assert_not_called()


def test_watcher_notices_validator_set_joining(
    validator_proxy_contract, non_validator_address, system_address, spawn
):
    control_queue = Queue()
    stop_callback = Mock()
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_contract,
        to_canonical_address(non_validator_address),
        poll_interval=poll_interval,
        control_queue=control_queue,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(False)
    stop_callback.assert_not_called()

    # join validator set
    validator_proxy_contract.functions.updateValidators(
        [non_validator_address]
    ).transact({"from": system_address})

    gevent.sleep(poll_interval * 1.5)  # check a second time
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(True)
    stop_callback.assert_not_called()


def test_watcher_notices_validator_set_leaving(
    validator_proxy_with_validators, validator_address, system_address, spawn
):
    control_queue = Queue()
    stop_callback = Mock()
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(validator_address),
        poll_interval=poll_interval,
        control_queue=control_queue,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(True)
    stop_callback.assert_not_called()

    # leave validator set
    validator_proxy_with_validators.functions.updateValidators([]).transact(
        {"from": system_address}
    )

    gevent.sleep(poll_interval)  # check a second time
    with Timeout(0.1):
        initial_status_check = control_queue.get()
    assert initial_status_check == IsValidatorCheck(False)
    stop_callback.assert_called_once()
