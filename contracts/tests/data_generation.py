import random
import rlp

from collections import namedtuple
from web3.datastructures import AttributeDict
from eth_utils import decode_hex, keccak
from eth_keys import keys


SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")

_REQUIRED_BLOCK_HEADER_LENGTH = 12
_PRIVATE_KEY_DEFAULT = keys.PrivateKey(b"1" * 32)
_TIMESTAMP_DEFAULT = 100

_random_generator = random.Random(0)


def random_hash():
    return bytes(_random_generator.randint(0, 255) for _ in range(32))


def random_number():
    return _random_generator.randint(0, 100)


def random_private_key():
    return keys.PrivateKey(random_hash())


def serialize_block_header(block_header):
    return [
        block_header.parentHash,
        block_header.sha3Uncles,
        block_header.author,
        block_header.stateRoot,
        block_header.transactionsRoot,
        block_header.receiptsRoot,
        block_header.logsBloom,
        block_header.difficulty,
        block_header.number,
        block_header.gasLimit,
        block_header.gasUsed,
        block_header.timestamp,
        block_header.extraData,
    ]


def sign_data(data, private_key):
    data_hash = keccak(data)
    return private_key.sign_msg_hash(data_hash).to_bytes()


def make_block_header(
    timestamp=_TIMESTAMP_DEFAULT, private_key=_PRIVATE_KEY_DEFAULT, use_short_list=False
):
    unsigned_block_header = AttributeDict(
        {
            "parentHash": random_hash(),
            "sha3Uncles": random_hash(),
            "author": decode_hex(private_key.public_key.to_address()),
            "stateRoot": random_hash(),
            "transactionsRoot": random_hash(),
            "receiptsRoot": random_hash(),
            "logsBloom": b"\x00" * 256,
            "difficulty": 0,
            "number": random_number(),
            "gasLimit": 0,
            "gasUsed": 0,
            "timestamp": timestamp,
            "extraData": random_hash(),
        }
    )

    unsigned_block_header_serialized = serialize_block_header(unsigned_block_header)

    if use_short_list:
        unsigned_block_header_serialized = unsigned_block_header_serialized[
            : _REQUIRED_BLOCK_HEADER_LENGTH - 1
        ]

    unsigned_block_header_encoded = rlp.encode(unsigned_block_header_serialized)
    signature = sign_data(unsigned_block_header_encoded, private_key)

    return SignedBlockHeader(unsigned_block_header_encoded, signature)


def make_random_signed_data(*, private_key=_PRIVATE_KEY_DEFAULT):
    random_data = random_hash()
    random_data_encoded = rlp.encode(random_data)
    signature = sign_data(random_data_encoded, private_key)

    return SignedBlockHeader(random_data_encoded, signature)
