import logging

import bridge.config
import bridge.main
import bridge.webservice


def test_reload_logging_config(write_config, caplog, minimal_config):
    def config_with_loglevel(level):
        return write_config(
            minimal_config + f'\n[logging.loggers."test.reload"]\nlevel = "{level}"\n'
        )

    caplog.set_level(logging.INFO)
    logger = logging.getLogger("test.reload")

    logger.debug("foo")
    assert not caplog.records

    bridge.main.reload_logging_config(config_with_loglevel("DEBUG"))
    assert caplog.records[-1].message.startswith("Logging has been reconfigured")

    caplog.clear()
    logger.debug("foo")
    assert caplog.records

    bridge.main.reload_logging_config(config_with_loglevel("INFO"))
    caplog.clear()
    logger.debug("foo")
    assert not caplog.records


def test_reload_logging_config_does_not_throw_config_gone(caplog):
    caplog.set_level(logging.INFO)
    bridge.main.reload_logging_config("/no/such/file")
    print(caplog.records)
    assert caplog.records[-1].message.startswith("Error while trying to reload")


def test_reload_logging_config_does_not_throw_malformed_toml(write_config, caplog):
    caplog.set_level(logging.INFO)
    bridge.main.reload_logging_config(write_config("[foo bar]  # malformed"))
    print(caplog.records)
    assert caplog.records[-1].message.startswith("Error while trying to reload")


def test_reload_logging_config_does_not_throw_schema_error(write_config, caplog):
    caplog.set_level(logging.INFO)
    bridge.main.reload_logging_config(write_config('[webservice]\nenabled = "foo"'))
    print(caplog.records)
    assert caplog.records[-1].message.startswith("Error while trying to reload")


def test_make_webservice_no_config(minimal_config, load_config_from_string):
    config = load_config_from_string(minimal_config)
    ws = bridge.main.make_webservice(
        config=config, recorder=bridge.main.make_recorder(config)
    )
    assert ws is None


def test_make_webservice(minimal_config, webservice_config, load_config_from_string):
    config = load_config_from_string(minimal_config + webservice_config)
    ws = bridge.main.make_webservice(
        config=config, recorder=bridge.main.make_recorder(config)
    )
    assert isinstance(ws, bridge.webservice.Webservice)
