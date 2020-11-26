import logging

import gevent
import tenacity
from eth_utils import is_canonical_address, to_checksum_address

from bridge.events import IsValidatorCheck

logger = logging.getLogger(__name__)

retry = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
)


class ValidatorStatusWatcher:
    def __init__(
        self,
        validator_proxy_contract,
        validator_address,
        poll_interval,
        control_queue,
        stop_validating_callback,
    ) -> None:
        self.validator_proxy_contract = validator_proxy_contract
        if not is_canonical_address(validator_address):
            raise ValueError("Validator address must be given in canonical format")
        self.validator_address = validator_address

        self.poll_interval = poll_interval
        self.control_queue = control_queue
        self.stop_validating_callback = stop_validating_callback

    def _wait_for_validator_status(self):
        """wait until address has validator status"""
        while not self.check_validator_status():
            logger.warning(
                f"The account with address {to_checksum_address(self.validator_address)} is not a "
                f"member of the validator set at the moment. This status will be checked "
                f"periodically."
            )
            gevent.sleep(self.poll_interval)

    def _wait_for_non_validator_status(self):
        """wait until address has lost its validator status"""
        while self.check_validator_status():
            gevent.sleep(self.poll_interval)

    def run(self) -> None:
        is_validator_from_beginning = self.check_validator_status()
        self.control_queue.put(IsValidatorCheck(is_validator_from_beginning))

        if not is_validator_from_beginning:
            self._wait_for_validator_status()
            self.control_queue.put(IsValidatorCheck(True))
        logger.info("The account is a member of the validator set")

        gevent.sleep(self.poll_interval)  # wait until we poll again
        self._wait_for_non_validator_status()

        logger.warning(
            f"The account with address {to_checksum_address(self.validator_address)} has lost its "
            f"validator status. The program will shutdown now."
        )
        self.control_queue.put(IsValidatorCheck(False))
        self.stop_validating_callback()

    @retry
    def check_validator_status(self):
        logger.debug("Checking validator status")
        return self.validator_proxy_contract.functions.isValidator(
            self.validator_address
        ).call()
