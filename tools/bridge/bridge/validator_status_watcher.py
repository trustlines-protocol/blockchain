import logging

import gevent
from eth_utils import is_canonical_address
from gevent.event import Event


class ValidatorStatusWatcher:
    def __init__(
        self, validator_proxy_contract, validator_address, poll_interval
    ) -> None:
        self.validator_proxy_contract = validator_proxy_contract
        if not is_canonical_address(validator_address):
            raise ValueError("Validator address must be given in canonical format")
        self.validator_address = validator_address

        self.poll_interval = poll_interval

        self.has_started_validating = Event()
        self.has_stopped_validating = Event()

        self.logger = logging.getLogger(
            "bridge.validation_status_watcher.ValidationStatusWatcher"
        )

    def run(self) -> None:
        while True:
            is_validator = self.check_validator_status()

            if is_validator and not self.has_started_validating.is_set():
                self.has_started_validating.set()
                self.logger.info("Starting to validate")

            if not is_validator and self.has_started_validating.is_set():
                self.has_stopped_validating.set()
                self.logger.info(
                    "Stopping to validate as we dropped out of the validator set"
                )
                break

            gevent.sleep(self.poll_interval)

    def check_validator_status(self):
        return self.validator_proxy_contract.functions.isValidator(
            self.validator_address
        ).call()
