from eth_typing import Hash32
from eth_utils import int_to_big_endian, keccak
from web3.datastructures import AttributeDict


def compute_transfer_hash(transfer_event: AttributeDict) -> Hash32:
    return Hash32(
        keccak(
            b"".join(
                [
                    bytes(transfer_event.transactionHash),
                    int_to_big_endian(transfer_event.logIndex),
                ]
            )
        )
    )
