import pytest
from eth_keys.constants import SECPK1_N
from toolz import dissoc

from bridge.config import (
    validate_checksum_address,
    validate_config,
    validate_non_negative_integer,
    validate_positive_float,
    validate_private_key,
    validate_rpc_url,
)


@pytest.fixture(scope="session")
def valid_config():
    return {
        "home_rpc_url": "url",
        "foreign_rpc_url": "url",
        "token_contract_address": "0x4B0b6E093a330c00fE614B804Ad59e9b0A4FE8A9",
        "foreign_bridge_contract_address": "0xbb1046b0fe450aa48deaff6fa474adbf972840dd",
    }


def test_validate_missing_keys(valid_config):
    invalid_config = dissoc(valid_config, "home_rpc_url")

    with pytest.raises(ValueError):
        validate_config(invalid_config)


def test_validate_unknown_keys(valid_config):
    with pytest.raises(ValueError):
        validate_config({**valid_config, "unknown_key": 1})


def test_validate_rpc_url():
    validate_rpc_url("https://localhost:8545")


def test_validate_invalid_rpc_url():
    with pytest.raises(TypeError):
        validate_rpc_url(1)


def test_validate_non_negative_integer():
    validate_non_negative_integer(0)


def test_validate_non_negative_integer_false_type():
    with pytest.raises(ValueError):
        validate_non_negative_integer(1.1)


def test_validate_non_negative_integer_negative():
    with pytest.raises(ValueError):
        validate_non_negative_integer(-1)


def test_validate_positive_float():
    validate_positive_float(1.1)


def test_validate_positive_float_int():
    validate_positive_float(5)


def test_validate_positive_float_false_type():
    with pytest.raises(ValueError):
        validate_positive_float("foo")


def test_validate_positive_float_negative():
    with pytest.raises(ValueError):
        validate_positive_float(-1.1)


def test_validate_address():
    validate_checksum_address("0x4B0b6E093a330c00fE614B804Ad59e9b0A4FE8A9")


def test_validate_address_invalid_format():
    with pytest.raises(ValueError):
        validate_checksum_address("0x0")


def test_validate_address_no_checksum():
    with pytest.raises(ValueError):
        validate_checksum_address("0x4b0b6e093a330c00fe614b804ad59e9b0a4fe8a9")


def test_private_key_no_dict():
    private_key = "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c"

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_raw():
    private_key = {
        "raw": "0x6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c"
    }
    validate_private_key(private_key)


def test_private_key_raw_no_string():
    private_key = {"raw": 1}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_raw_no_hex():
    private_key = {"raw": "no_hex"}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_raw_missing_0x_prefix():
    private_key = {
        "raw": "6370fd033278c143179d81c5526140625662b8daa446c22ee2d73db3707e620c"
    }

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_raw_too_short():
    private_key = {"raw": "0x6370fd033278c143179d"}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_raw_out_of_range():
    private_key = {"raw": str(hex(SECPK1_N))}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_keystore():
    private_key = {
        "keystore_path": "keystore.json",
        "keystore_password_path": "password",
    }
    validate_private_key(private_key)


def test_private_key_keystore_no_string():
    private_key = {"keystore_path": "keystore.json", "keystore_password_path": 1}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_keystore_empty():
    private_key = {"keystore_path": "keystore.json", "keystore_password_path": ""}

    with pytest.raises(ValueError):
        validate_private_key(private_key)


def test_private_key_missing_field():
    private_key = {"keystore_path": "keystore.json"}

    with pytest.raises(ValueError):
        validate_private_key(private_key)
