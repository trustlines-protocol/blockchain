import logging
from typing import Optional

import gevent
from eth_utils import is_canonical_address, to_checksum_address

logger = logging.getLogger(__name__)


class ValidatorStatusWatcher:
    def __init__(
        self,
        validator_proxy_contract,
        validator_address,
        poll_interval,
        start_validating_callback,
        stop_validating_callback,
    ) -> None:
        self.validator_proxy_contract = validator_proxy_contract
        if not is_canonical_address(validator_address):
            raise ValueError("Validator address must be given in canonical format")
        self.validator_address = validator_address

        self.poll_interval = poll_interval
        self.start_validating_callback = start_validating_callback
        self.stop_validating_callback = stop_validating_callback

        self.is_validating: Optional[bool] = None

        self.logger = logging.getLogger(
            "bridge.validation_status_watcher.ValidationStatusWatcher"
        )

    def run(self) -> None:
        self.is_validating = self.check_validator_status()
        if self.is_validating:
            self.logger.info("The account is a member of the validator set")
            self.start_validating_callback()
        else:
            self.logger.warning(
                f"The account with address {to_checksum_address(self.validator_address)} is not a "
                f"member of the validator set at the moment. This status will be checked "
                f"periodically."
            )

        while True:
            gevent.sleep(self.poll_interval)

            has_been_validating_before = self.is_validating
            self.is_validating = self.check_validator_status()

            if self.is_validating and not has_been_validating_before:
                logger.info("Account joined the validator set")
                self.start_validating_callback()
            elif not self.is_validating and has_been_validating_before:
                logger.info("Account has left the validator set")
                self.stop_validating_callback()

    def check_validator_status(self):
        self.logger.debug("Checking validator status")
        return self.validator_proxy_contract.functions.isValidator(
            self.validator_address
        ).call()
