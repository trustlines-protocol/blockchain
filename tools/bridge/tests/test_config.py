import pytest

from toolz import dissoc

from bridge.config import (
    validate_config,
    validate_rpc_url,
    validate_positive_integer,
    validate_positive_float,
    validate_checksum_address,
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
    with pytest.raises(ValueError):
        validate_rpc_url(1)


def test_validate_positive_integer():
    validate_positive_integer(0)


def test_validate_positive_integer_false_type():
    with pytest.raises(ValueError):
        validate_positive_integer(1.1)


def test_validate_positive_integer_negative():
    with pytest.raises(ValueError):
        validate_positive_integer(-1)


def test_validate_positive_float():
    validate_positive_float(1.1)


def test_validate_positive_float_false_type():
    with pytest.raises(ValueError):
        validate_positive_float("1.1")


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
