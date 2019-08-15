import gevent

from bridge.validator_status_watcher import ValidatorStatusWatcher


def test_watcher_checks_status_correctly_for_validator(
    validator_proxy_with_validators, validator_address, spawn
):
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators, validator_address, poll_interval=1
    )
    assert validator_status_watcher.check_validator_status()
    assert not validator_status_watcher.has_started_validating.is_set()
    assert not validator_status_watcher.has_stopped_validating.is_set()

    spawn(validator_status_watcher.run)
    with gevent.timeout(0.01):
        validator_status_watcher.has_started_validating.wait()
    assert not validator_status_watcher.has_stopped_validating.is_set()


def test_watcher_checks_status_correctly_for_non_validator(
    validator_proxy_with_validators, non_validator_address, spawn
):
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators, non_validator_address, poll_interval=1
    )
    assert not validator_status_watcher.check_validator_status()
    assert not validator_status_watcher.has_started_validating.is_set()
    assert not validator_status_watcher.has_stopped_validating.is_set()

    spawn(validator_status_watcher.run)
    gevent.sleep(0.01)
    assert not validator_status_watcher.has_started_validating.is_set()
    assert not validator_status_watcher.has_stopped_validating.is_set()


def test_watcher_notices_validator_set_joining(
    validator_proxy_contract, non_validator_address, system_address, spawn
):
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_contract, non_validator_address, poll_interval=poll_interval
    )

    spawn(validator_status_watcher.run)

    validator_proxy_contract.functions.updateValidators(
        [non_validator_address]
    ).transact({"from": system_address})

    with gevent.timeout(2 * poll_interval):
        validator_status_watcher.has_started_validating.wait()
    assert not validator_status_watcher.has_stopped_validating.is_set()


def test_watcher_notices_validator_set_leaving(
    validator_proxy_with_validators, validator_address, system_address, spawn
):
    poll_interval = 0.1
    validator_status_watcher = ValidatorStatusWatcher(
        validator_proxy_with_validators, validator_address, poll_interval=poll_interval
    )

    spawn(validator_status_watcher.run)
    with gevent.timeout(0.01):
        validator_status_watcher.has_started_validating.wait()

    validator_proxy_with_validators.functions.updateValidators([]).transact(
        {"from": system_address}
    )

    with gevent.timeout(2 * poll_interval):
        validator_status_watcher.has_stopped_validating.wait()
    assert not validator_status_watcher.has_started_validating.is_set()
