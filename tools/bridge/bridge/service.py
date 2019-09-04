import logging

import gevent

logger = logging.getLogger(__name__)


class Service:
    def __init__(self, name: str, run, *args, **kwargs):
        self.name = name
        self.run = run
        self.args = args
        self.kwargs = kwargs


def start_services(services, start=gevent.Greenlet.start, link_exception_callback=None):
    greenlets = []
    for s in services:
        logger.info(f"Starting {s.name} service")
        gr = gevent.Greenlet(s.run, *s.args, **s.kwargs)
        gr.name = s.name
        if link_exception_callback is not None:
            gr.link_exception(link_exception_callback)
        start(gr)
        greenlets.append(gr)
    return greenlets


def run_services(services):
    try:
        greenlets = start_services(services)
        gevent.joinall(greenlets, raise_error=True)
    finally:
        for greenlet in greenlets:
            greenlet.kill()
