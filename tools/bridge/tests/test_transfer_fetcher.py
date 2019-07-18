import gevent
from gevent import Greenlet
from gevent.queue import Queue

from bridge.transfer_fetcher import fetch_transfer_events


def test_transfer_event_fetcher(w3_foreign, tester_foreign):
    queue = Queue()
    try:
        transfer_event_fetcher = Greenlet.spawn(
            fetch_transfer_events, w3_foreign, queue, 0.1
        )
        assert queue.get() == 0
        assert queue.empty()
        gevent.sleep(0.3)
        assert queue.empty()
        tester_foreign.mine_block()
        gevent.sleep(0.3)
        assert queue.get() == 1
        assert queue.empty()
    finally:
        transfer_event_fetcher.kill()
