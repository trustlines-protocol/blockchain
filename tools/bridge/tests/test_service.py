import copy
from unittest.mock import MagicMock

import gevent
import pytest

from bridge.service import Service, run_services, start_services


@pytest.fixture()
def service():
    def run():
        pass

    service = Service("service_name", run)
    return service


@pytest.fixture()
def error_raising_service():
    def run():
        raise ValueError

    service = Service(name="error_service_name", run=run)
    return service


def test_start_service_will_start_greenlets(service):
    """
    Tests that `start_services` returns a list of started greenlets
    """
    services = [service, copy.deepcopy(service)]
    started_greenlets = start_services(services)

    for started_greenlet in started_greenlets:
        assert started_greenlet.started
        assert started_greenlet.name == "service_name"
        started_greenlet.kill()


def test_start_service_arguments():
    """
    Tests that the correct arguments are given to the service ran
    """
    args = (2, 4)
    kwargs = {"ten": 10, "twenty": 20}
    mocked_run = MagicMock()

    service = Service("service_name", mocked_run, *args, **kwargs)
    started_greenlets = start_services([service])
    gevent.joinall(started_greenlets, raise_error=True)

    mocked_run.assert_called_with(*args, **kwargs)


def test_start_service_callback(error_raising_service):
    """
    Tests that the link_exception_callback will be called when the started service dies raising an error.
    """
    mocked_callback = MagicMock()
    started_greenlets = start_services(
        [error_raising_service], link_exception_callback=mocked_callback
    )
    gevent.joinall(started_greenlets)

    mocked_callback.assert_called_once()


def test_run_services():
    mocked_run = MagicMock()
    service = Service(name="mocked_service", run=mocked_run)
    run_services([service])
    mocked_run.assert_called_once()
