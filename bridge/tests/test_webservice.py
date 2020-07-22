import falcon.testing
import pytest

import bridge.main


@pytest.fixture
def webservice(minimal_config, webservice_config, load_config_from_string):
    config = load_config_from_string(minimal_config + webservice_config)
    ws = bridge.main.make_webservice(
        config=config, recorder=bridge.main.make_recorder(config)
    )
    assert isinstance(ws, bridge.webservice.Webservice)
    return ws


@pytest.fixture
def client(webservice):
    return falcon.testing.TestClient(webservice.app)


def test_welcome_page(client):
    result = client.simulate_get("/")
    assert result.status == "200 OK"
    print(result.text)
    assert "Welcome to tlbc-bridge" in result.text
    assert result.headers["content-type"] == "text/html"


def test_internal_state(client):
    result = client.simulate_get("/bridge/internal-state")
    assert result.status == "200 OK"
    r = result.json
    print(r)
    assert isinstance(r, dict)
    assert "bridge" in r
