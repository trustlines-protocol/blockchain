import logging

import gevent
from eth_utils import from_wei

logger = logging.getLogger(__name__)


class ValidatorBalanceWatcher:
    def __init__(
        self, w3, validator_address, poll_interval, balance_warn_threshold
    ) -> None:
        self.w3 = w3
        self.validator_address = validator_address
        self.poll_interval = poll_interval
        self.balance_warn_threshold = balance_warn_threshold

    def run(self) -> None:
        while True:
            current_balance = self.w3.eth.getBalance(self.validator_address)
            if current_balance < self.balance_warn_threshold:
                logger.warn(
                    f"Low balance of validator account: {from_wei(current_balance, 'ether')} "
                    f"TLC"
                )

            gevent.sleep(self.poll_interval)
