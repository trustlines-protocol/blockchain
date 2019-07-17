import pytest

from bridge.config import validate_config


def test_validate_missing_keys():
    with pytest.raises(ValueError):
        validate_config(
            {
                "home-rpc-url": "url",
                # "foreign-rpc-url": missing,
            }
        )


def test_validate_unknown_keys():
    with pytest.raises(ValueError):
        validate_config(
            {"home-rpc-url": "url", "foreign-rpc-url": "url", "unknown-key": 123}
        )
