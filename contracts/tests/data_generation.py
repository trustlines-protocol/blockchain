import random
import rlp
import codecs

from collections import namedtuple
from web3.datastructures import AttributeDict
from eth_utils import decode_hex, keccak
from eth_keys import keys


SignedBlockHeader = namedtuple("SignedBlockHeader", "unsignedBlockHeader signature")

_REQUIRED_BLOCK_HEADER_LENGTH = 12

_RANDOM_GENERATOR = random.Random(0)
_PRIVATE_KEY_DEFAULT = keys.PrivateKey(b"1" * 32)


def random_hash():
    return bytes(_RANDOM_GENERATOR.randint(0, 255) for _ in range(32))


def random_number():
    return _RANDOM_GENERATOR.randint(0, 100)


def random_private_key():
    return keys.PrivateKey(random_hash())


def encode_block_header(block_header):
    block_header_serialzied = [
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

    return rlp.encode(block_header_serialzied)


def make_equivocated_signed_block_header(
    *,
    use_incorrect_structure=False,
    use_short_list=False,
    timestamp=100,
    private_key=_PRIVATE_KEY_DEFAULT,
):
    """Generates an equivocated signed block header.

    Each pair of generated block header by this function are equivocated.
    This is true unless a parameter gets adjusted. Then it can hold true.
    Trough the parameters, the generation could be varied to get manipulated
    block headers related to the relevant properties of equivocated blocks.
    The configuration of the generation can be used to test the various rules of
    the equivocation proof.
    """

    block_header_encoded = None

    if use_incorrect_structure:
        block_header = codecs.decode("123456789abcde", "hex")
        block_header_encoded = rlp.encode(block_header)

    else:
        block_header = AttributeDict(
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
                "timestamp": int(timestamp),
                "extraData": random_hash(),
            }
        )

        block_header_encoded = encode_block_header(block_header)

        if use_short_list:
            block_header_decoded = rlp.decode(block_header_encoded)
            block_header_encoded = rlp.encode(
                block_header_decoded[: _REQUIRED_BLOCK_HEADER_LENGTH - 1]
            )

    block_header_hash = keccak(block_header_encoded)
    signature = private_key.sign_msg_hash(block_header_hash).to_bytes()

    # TODO: short header

    return SignedBlockHeader(block_header_encoded, signature)
