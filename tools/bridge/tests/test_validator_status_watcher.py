from unittest.mock import Mock

import gevent
from eth_utils import to_canonical_address

from bridge.validator_status_watcher import ValidatorStatusWatcher


def test_watcher_checks_initial_validator_status_correctly(
    validator_proxy_with_validators, validator_address, spawn
):
    start_callback = Mock()
    stop_callback = Mock()
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(validator_address),
        poll_interval=1,
        start_validating_callback=start_callback,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    gevent.sleep(0.01)
    start_callback.assert_called_once()
    stop_callback.assert_not_called()


def test_watcher_checks_initial_non_validator_status_correctly(
    validator_proxy_with_validators, non_validator_address, spawn
):
    start_callback = Mock()
    stop_callback = Mock()
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(non_validator_address),
        poll_interval=1,
        start_validating_callback=start_callback,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    gevent.sleep(0.01)
    start_callback.assert_not_called()
    stop_callback.assert_not_called()


def test_watcher_notices_validator_set_joining(
    validator_proxy_contract, non_validator_address, system_address, spawn
):
    start_callback = Mock()
    stop_callback = Mock()
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_contract,
        to_canonical_address(non_validator_address),
        poll_interval=poll_interval,
        start_validating_callback=start_callback,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    gevent.sleep(0.01)  # check initial status
    start_callback.assert_not_called()
    stop_callback.assert_not_called()

    # join validator set
    validator_proxy_contract.functions.updateValidators(
        [non_validator_address]
    ).transact({"from": system_address})

    gevent.sleep(poll_interval * 1.5)  # check a second time
    start_callback.assert_called_once()
    stop_callback.assert_not_called()


def test_watcher_notices_validator_set_leaving(
    validator_proxy_with_validators, validator_address, system_address, spawn
):
    start_callback = Mock()
    stop_callback = Mock()
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators,
        to_canonical_address(validator_address),
        poll_interval=poll_interval,
        start_validating_callback=start_callback,
        stop_validating_callback=stop_callback,
    )

    spawn(validator_status_watcher.run)
    gevent.sleep(poll_interval * 0.01)  # check initial status
    start_callback.assert_called_once()
    stop_callback.assert_not_called()

    start_callback.reset_mock()

    # leave validator set
    validator_proxy_with_validators.functions.updateValidators([]).transact(
        {"from": system_address}
    )

    gevent.sleep(poll_interval)  # check a second time
    start_callback.assert_not_called()
    stop_callback.assert_called_once()
