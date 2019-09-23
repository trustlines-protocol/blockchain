import random
from collections import namedtuple

import rlp
from eth_keys import keys
from eth_utils import decode_hex, keccak
from web3.datastructures import AttributeDict

SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")

_PRIVATE_KEY_DEFAULT = keys.PrivateKey(b"1" * 32)
_TIMESTAMP_DEFAULT = 100

_random_generator = random.Random(0)


def random_hash():
    return bytes(_random_generator.randint(0, 255) for _ in range(32))


def random_number():
    return _random_generator.randint(0, 100)


def random_private_key():
    return keys.PrivateKey(random_hash())


def make_short_block_header_list(block_header):
    """Order the first 11 block header fields into a list.

    The number relates to the minimum required block header fields by the
    equivocation proof implementation in the contracts. Using the short header
    list of a block will lead to an exception.
    """
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
    ]


def make_full_block_header_list(block_header):
    """Order all block header fields into a list."""
    return make_short_block_header_list(block_header) + [
        block_header.timestamp,
        block_header.extraData,
    ]


def sign_data(data, private_key):
    data_hash = keccak(data)
    return private_key.sign_msg_hash(data_hash).to_bytes()


def make_block_header(
    timestamp=_TIMESTAMP_DEFAULT, private_key=_PRIVATE_KEY_DEFAULT, use_short_list=False
):
    """Generates a signed block header

    :param timestamp: timestamp field of the block header, optional
    :param private_key: used for the author field of the block as well as for
                        signing the block header, optional
    :use_short_list:    when set, the list of block header fields will be
                        truncated and the short version will not be accepted by
                        the equivocation proof
    :returns: unsigned block header list in RLP encoding and the related signature
    """
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

    if use_short_list:
        unsigned_block_header_list = make_short_block_header_list(unsigned_block_header)

    else:
        unsigned_block_header_list = make_full_block_header_list(unsigned_block_header)

    unsigned_block_header_encoded = rlp.encode(unsigned_block_header_list)
    signature = sign_data(unsigned_block_header_encoded, private_key)

    return SignedBlockHeader(unsigned_block_header_encoded, signature)


def make_random_signed_data(*, private_key=_PRIVATE_KEY_DEFAULT):
    random_data = random_hash()
    random_data_encoded = rlp.encode(random_data)
    signature = sign_data(random_data_encoded, private_key)

    return SignedBlockHeader(random_data_encoded, signature)
