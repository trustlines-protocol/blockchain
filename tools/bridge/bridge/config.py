from typing import Any, Dict

import toml
from eth_keys.constants import SECPK1_N
from eth_utils import (
    big_endian_to_int,
    decode_hex,
    encode_hex,
    is_0x_prefixed,
    is_checksum_address,
    is_hex,
    to_canonical_address,
    to_checksum_address,
    to_wei,
)
from eth_utils.toolz import merge
from marshmallow import Schema, fields, validate, validates_schema
from marshmallow.exceptions import ValidationError

FORCED_LOGGING_CONFIG = {"version": 1, "incremental": True}


class LoggingField(fields.Mapping):
    def _serialize(self, value: dict, attr: str, obj: Any, **kwargs) -> str:
        return super()._serialize(value, attr, obj, **kwargs)

    def _deserialize(self, value: Any, attr: str, obj: Any, **kwargs) -> bytes:
        deserialized = super()._deserialize(value, attr, obj, **kwargs)
        return merge(FORCED_LOGGING_CONFIG, deserialized)


class AddressField(fields.Field):
    def _serialize(self, value: bytes, attr: str, obj: Any, **kwargs) -> str:
        return to_checksum_address(value)

    def _deserialize(self, value: Any, attr: str, obj: Any, **kwargs) -> bytes:
        if not isinstance(value, str) or not is_checksum_address(value):
            raise ValidationError(
                f"{attr} must be a checksum formatted address, but got {value}"
            )
        return to_canonical_address(value)


class PrivateKeyField(fields.Field):
    def _serialize(self, value: bytes, attr: str, obj: Any, **kwargs) -> str:
        return encode_hex(value)

    def _deserialize(self, value: Any, attr: str, obj: Any, **kwargs) -> bytes:
        if not isinstance(value, str) or not is_hex(value) or not is_0x_prefixed(value):
            raise ValidationError(
                f"{attr} must be a 0x prefixed hex string, but got {value}"
            )

        raw_key_bytes = decode_hex(value)
        if len(raw_key_bytes) != 32:
            raise ValidationError(
                f"{attr} must be a 32 bytes private key, got {len(value)} bytes"
            )

        raw_key_int = big_endian_to_int(raw_key_bytes)
        if not 0 < raw_key_int < SECPK1_N:
            raise ValueError(
                f"{attr} must be a valid private key, but it's out of range"
            )

        return raw_key_bytes


class PrivateKeySchema(Schema):
    raw = PrivateKeyField(required=False)
    keystore_path = fields.String(required=False)
    keystore_password_path = fields.String(required=False)

    @validates_schema
    def validate_schema(self, in_data, **kwargs):
        raw_given = "raw" in in_data
        keystore_given = "keystore_path" in in_data
        password_given = "keystore_password_path" in in_data

        if raw_given and (keystore_given or password_given):
            raise ValidationError(
                "Either 'raw' or 'keystore_path' in conjunction with 'keystore_password_path' "
                "must be given, but not both"
            )
        elif not raw_given and (not keystore_given or not password_given):
            raise ValidationError(
                "If 'raw' is not given, both 'keystore_path' and 'keystore_password_path' must be "
                "given"
            )


validate_non_negative = validate.Range(min=0)


class ConfigSchema(Schema):
    home_rpc_url = fields.Url(required=True)
    home_bridge_contract_address = AddressField(required=True)
    foreign_rpc_url = fields.Url(required=True)
    foreign_chain_token_contract_address = AddressField(required=True)
    foreign_bridge_contract_address = AddressField(required=True)
    validator_private_key = fields.Nested(PrivateKeySchema, required=True)

    logging = LoggingField(missing=lambda: dict(FORCED_LOGGING_CONFIG))
    home_rpc_timeout = fields.Integer(missing=180, validate=validate_non_negative)
    home_chain_gas_price = fields.Integer(
        missing=10 * 1000000000, validate=validate_non_negative
    )  # Gas price is in GWei
    home_chain_max_reorg_depth = fields.Integer(
        missing=1, validate=validate_non_negative
    )
    home_chain_event_poll_interval = fields.Float(
        missing=5, validate=validate_non_negative
    )
    home_chain_event_fetch_start_block_number = fields.Integer(
        missing=0, validate=validate_non_negative
    )
    foreign_rpc_timeout = fields.Integer(missing=180, validate=validate_non_negative)
    foreign_chain_max_reorg_depth = fields.Integer(
        missing=10, validate=validate_non_negative
    )
    foreign_chain_event_poll_interval = fields.Integer(
        missing=5, validate=validate_non_negative
    )
    foreign_chain_event_fetch_start_block_number = fields.Integer(
        missing=0, validate=validate_non_negative
    )
    balance_warn_poll_interval = fields.Float(
        missing=60, validate=validate_non_negative
    )
    # disable type check as type hint in eth_utils is wrong, (see
    # https://github.com/ethereum/eth-utils/issues/168)
    minimum_validator_balance = fields.Integer(
        missing=to_wei(0.04, "ether"),  # type: ignore
        validate=validate_non_negative,
    )


config_schema = ConfigSchema()


def load_config(path: str) -> Dict[str, Any]:
    if path is None:
        user_config = {}
    else:
        user_config = toml.load(path)

    return config_schema.load(user_config)
