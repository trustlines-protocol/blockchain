import bridge.config

example_logging_config = """
[logging.root]
level = "DEBUG"

[logging.loggers."bridge.main"]
level = "DEBUG"

# web3 is too verbose with level debug
[logging.loggers.web3]
level = "INFO"

[logging.loggers.urllib3]
level = "INFO"
"""


def test_load_minimal_config(write_config, minimal_config):
    cfg = bridge.config.load_config(write_config(minimal_config))
    print(cfg)

    assert cfg["logging"] == bridge.config.FORCED_LOGGING_CONFIG
    assert cfg["webservice"] == {}

    # make sure we have some sensible defaults
    assert cfg["home_chain"]["gas_price"] >= 10 ** 9
    assert cfg["home_chain"]["event_fetch_start_block_number"] == 0
    assert cfg["home_chain"]["max_reorg_depth"] >= 5

    assert cfg["foreign_chain"]["event_fetch_start_block_number"] == 0
    assert cfg["foreign_chain"]["max_reorg_depth"] >= 10


def test_logging_key(write_config, minimal_config):
    cfg = bridge.config.load_config(
        write_config(minimal_config + "\n" + example_logging_config)
    )
    print(cfg)
    assert cfg["logging"]["version"] == 1
    assert cfg["logging"]["incremental"] is True
    assert cfg["logging"]["loggers"]["bridge.main"] == {"level": "DEBUG"}
