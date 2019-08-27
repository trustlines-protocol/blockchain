import os
from typing import Any, Dict

import toml
import validators
from eth_keys.constants import SECPK1_N
from eth_utils import (
    big_endian_to_int,
    decode_hex,
    is_0x_prefixed,
    is_checksum_address,
    is_hex,
    to_canonical_address,
    to_wei,
)
from eth_utils.toolz import merge

from bridge.utils import dotted_key_dict_to_nested_dict, lower_dict_keys


def validate_rpc_url(url: Any) -> str:
    if not validators.url(url):
        raise ValueError(f"{url} is not a valid RPC url")
    return url


def validate_non_negative_integer(number: Any) -> int:
    if str(number) != str(int(number)):
        raise ValueError(f"{number} is not a valid integer")
    if not isinstance(number, int):
        number = int(number)
    if number < 0:
        raise ValueError(f"{number} must be greater than or equal zero")
    return number


def validate_positive_float(number: Any) -> float:
    if str(number) != str(float(number)) and str(number) != str(int(number)):
        raise ValueError(f"{number} is not a valid float")
    if not isinstance(number, float):
        number = float(number)
    if number <= 0:
        raise ValueError(f"{number} must be positive")
    return number


def validate_checksum_address(address: Any) -> bytes:
    if not is_checksum_address(address):
        raise ValueError(f"{address} is not a valid Ethereum checksum address")
    return to_canonical_address(address)


def validate_private_key(private_key: Any) -> dict:
    """ Validate the private key section of the configuration.

    The private key can be provided in two different ways. First is the
    unencrypted hex String representation of the raw private key. Alternatively
    it can be defined by a path to an encrypted keystore plus an according
    password file.
    This validation does only check the structure and the syntax of the
    configuration section. It does not include to verify correct paths nor
    gets the key decrypted. The key extraction must happen where else, because
    the configuration is meant to be reloadable, while the private key should
    persist from the start.
    """

    if not isinstance(private_key, dict):
        raise ValueError(
            f"Private key must be a dictionary with a raw key or a private keystore!"
        )

    if "raw" in private_key:
        raw_key = private_key["raw"]

        if not isinstance(raw_key, str):
            raise ValueError(f"Raw private key must be a string, got '{raw_key}'")

        if not is_hex(raw_key):
            raise ValueError(f"Raw private key must be hex encoded, got '{raw_key}'")

        if not is_0x_prefixed(raw_key):
            raise ValueError(
                f"Raw private key must have a `0x` prefix, got '{raw_key}'"
            )

        raw_key_bytes = decode_hex(raw_key)

        if len(raw_key_bytes) != 32:
            raise ValueError(
                f"Raw private key must represent 32 bytes, got '{raw_key}'"
            )

        raw_key_int = big_endian_to_int(raw_key_bytes)

        if not 0 < raw_key_int < SECPK1_N:
            raise ValueError(f"Raw private key outside of allowed range: '{raw_key}'")

    else:
        if (
            "keystore_path" not in private_key
            or "keystore_password_path" not in private_key
        ):
            raise ValueError(
                "The private key must be either defined by a raw hex string or "
                "by the file paths to a keystore and according password!"
            )

        keystore_path = private_key["keystore_path"]
        keystore_password_path = private_key["keystore_password_path"]

        if not isinstance(keystore_path, str) or not keystore_path:
            raise ValueError(
                f"Private keystore parameter seem to be no path, got '{keystore_path}'"
            )

        if not isinstance(keystore_password_path, str) or not keystore_password_path:
            raise ValueError(
                f"Private keystore password parameter seem to be no path, got '{keystore_password_path}'"
            )

    return private_key


def validate_logging(logging_dict: Dict) -> Dict:
    """validate the logging dictionary

    We don't do much here, but instead rely on the main function to
    catch errors from logging.config.dictConfig
    """
    if not isinstance(logging_dict, dict):
        raise ValueError("logging must be a dictionary")
    return merge({"version": 1, "incremental": True}, logging_dict)


REQUIRED_CONFIG_ENTRIES = [
    "home_rpc_url",
    "home_bridge_contract_address",
    "foreign_rpc_url",
    "foreign_chain_token_contract_address",
    "foreign_bridge_contract_address",
    "validator_private_key",
]

OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS: Dict[str, Any] = {
    "logging": {},
    "home_rpc_timeout": 180,
    "home_chain_gas_price": 10 * 1000000000,  # Gas price is in GWei
    "home_chain_max_reorg_depth": 1,
    "home_chain_event_poll_interval": 5,
    "home_chain_event_fetch_start_block_number": 0,
    "foreign_rpc_timeout": 180,
    "foreign_chain_max_reorg_depth": 10,
    "foreign_chain_event_poll_interval": 5,
    "foreign_chain_event_fetch_start_block_number": 0,
    "balance_warn_poll_interval": 60,
    # disable type check as type hint in eth_utils is wrong, (see
    # https://github.com/ethereum/eth-utils/issues/168)
    "minimum_validator_balance": to_wei(0.04, "ether"),  # type: ignore
}

CONFIG_ENTRY_VALIDATORS = {
    "logging": validate_logging,
    "home_rpc_url": validate_rpc_url,
    "home_rpc_timeout": validate_non_negative_integer,
    "home_chain_gas_price": validate_non_negative_integer,
    "home_chain_max_reorg_depth": validate_non_negative_integer,
    "home_bridge_contract_address": validate_checksum_address,
    "home_chain_event_poll_interval": validate_non_negative_integer,
    "home_chain_event_fetch_start_block_number": validate_non_negative_integer,
    "foreign_rpc_url": validate_rpc_url,
    "foreign_rpc_timeout": validate_non_negative_integer,
    "foreign_chain_max_reorg_depth": validate_non_negative_integer,
    "foreign_chain_event_poll_interval": validate_non_negative_integer,
    "foreign_chain_token_contract_address": validate_checksum_address,
    "foreign_bridge_contract_address": validate_checksum_address,
    "foreign_chain_event_fetch_start_block_number": validate_non_negative_integer,
    "validator_private_key": validate_private_key,
    "balance_warn_poll_interval": validate_positive_float,
    "minimum_validator_balance": validate_positive_float,
}

assert all(key in CONFIG_ENTRY_VALIDATORS for key in REQUIRED_CONFIG_ENTRIES)
assert all(
    key in CONFIG_ENTRY_VALIDATORS for key in OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS
)


def load_config_from_environment():
    result = {}

    # Support "nested" environment variables with a dot in their name.
    # Equivalent to a subsection within the TOML file.
    nested_environment_variables = dotted_key_dict_to_nested_dict(os.environ)

    keys = set(
        REQUIRED_CONFIG_ENTRIES
        + list(OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS.keys())
        + list(CONFIG_ENTRY_VALIDATORS.keys())
    )
    for key in keys:
        if nested_environment_variables.get(key.upper()):
            result[key] = nested_environment_variables.get(key.upper())

    # Make sure that the nested keys from the environment variables are all
    # lower case as well.
    return lower_dict_keys(result)


def load_config(path: str) -> Dict[str, Any]:
    if path is None:
        user_config = {}
    else:
        user_config = toml.load(path)

    environment_config = load_config_from_environment()

    config = merge(
        OPTIONAL_CONFIG_ENTRIES_WITH_DEFAULTS, user_config, environment_config
    )

    return validate_config(config)


def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
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

    # check for validity of entries
    validated_config = {}
    for key, value in config.items():
        try:
            validated_config[key] = CONFIG_ENTRY_VALIDATORS[key](value)
        except ValueError as value_error:
            raise ValueError(f"Invalid config entry {key}: {value_error}")

    return validated_config
