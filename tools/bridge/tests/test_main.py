import logging

import bridge.main


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
