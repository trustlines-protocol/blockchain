import bridge.config

minimal_config = """
[foreign_chain]
rpc_url = "http://localhost:9200"
token_contract_address = "0x731a10897d267e19B34503aD902d0A29173Ba4B1"
bridge_contract_address = "0xb4c79daB8f259C7Aee6E5b2Aa729821864227e84"

[home_chain]
rpc_url = "http://localhost:9100"
bridge_contract_address = "0x771434486a221c6146F27B72fd160Bdf0eb1288e"

[validator_private_key]
raw = "0xb8dcbb8a564483279579e04bffacbd76f79df157cfbebed84079673b32d9e72f"
"""

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


def test_load_minimal_config(write_config):
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


def test_logging_key(write_config):
    cfg = bridge.config.load_config(
        write_config(minimal_config + "\n" + example_logging_config)
    )
    print(cfg)
    assert cfg["logging"]["version"] == 1
    assert cfg["logging"]["incremental"] is True
    assert cfg["logging"]["loggers"]["bridge.main"] == {"level": "DEBUG"}
