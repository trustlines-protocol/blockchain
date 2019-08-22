import logging

import gevent
import tenacity

from bridge.events import BalanceCheck

logger = logging.getLogger(__name__)

retry = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
)


class ValidatorBalanceWatcher:
    def __init__(self, w3, validator_address, poll_interval, control_queue) -> None:
        self.w3 = w3
        self.validator_address = validator_address
        self.poll_interval = poll_interval
        self.control_queue = control_queue

    @retry
    def _rpc_get_balance(self):
        return self.w3.eth.getBalance(self.validator_address)

    def run(self) -> None:
        while True:
            current_balance = self._rpc_get_balance()
            self.control_queue.put(BalanceCheck(current_balance))
            gevent.sleep(self.poll_interval)
