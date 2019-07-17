import toml

from eth_utils.toolz import merge


REQUIRED_CONFIG_ENTRIES = ["home-rpc-url", "foreign-rpc-url"]

OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS = {}


def load_config(path):
    if path is None:
        user_config = {}
    else:
        user_config = toml.load(path)

    config = merge(OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS, user_config)

    validate_config(config)

    return config


def validate_config(config):
    # check for missing keys
    for required_key in REQUIRED_CONFIG_ENTRIES:
        if required_key not in config:
            raise ValueError(f"Config is missing required key {required_key}")

    # check for unknown keys
    for key in config.keys():
        if (
            key not in REQUIRED_CONFIG_ENTRIES
            and key not in OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS
        ):
            raise ValueError(f"Config contains unknown key {key}")
