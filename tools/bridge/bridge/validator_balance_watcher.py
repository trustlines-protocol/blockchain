import logging

import gevent
from eth_utils import from_wei

from bridge.control_events import BalanceCheck

logger = logging.getLogger(__name__)


class ValidatorBalanceWatcher:
    def __init__(
        self,
        w3,
        validator_address,
        poll_interval,
        balance_warn_threshold,
        control_queue,
    ) -> None:
        self.w3 = w3
        self.validator_address = validator_address
        self.poll_interval = poll_interval
        self.balance_warn_threshold = balance_warn_threshold
        self.control_queue = control_queue

    def run(self) -> None:
        while True:
            current_balance = self.w3.eth.getBalance(self.validator_address)
            if current_balance < self.balance_warn_threshold:
                logger.warn(
                    f"Low balance of validator account: {from_wei(current_balance, 'ether')} "
                    f"TLC"
                )

            self.control_queue.put(BalanceCheck(current_balance))

            gevent.sleep(self.poll_interval)
