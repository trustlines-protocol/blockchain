import logging

import gevent

from bridge.control_events import BalanceCheck

logger = logging.getLogger(__name__)


class ValidatorBalanceWatcher:
    def __init__(self, w3, validator_address, poll_interval, control_queue) -> None:
        self.w3 = w3
        self.validator_address = validator_address
        self.poll_interval = poll_interval
        self.control_queue = control_queue

    def run(self) -> None:
        while True:
            current_balance = self.w3.eth.getBalance(self.validator_address)
            self.control_queue.put(BalanceCheck(current_balance))
            gevent.sleep(self.poll_interval)
