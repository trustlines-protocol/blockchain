from os import R_OK, access
from os.path import isfile

from eth_keyfile import extract_key_from_keyfile
from eth_typing import Hash32
from eth_utils import decode_hex, int_to_big_endian, keccak
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


def get_validator_private_key(config: dict) -> bytes:
    """Get the private key of the validator from the configuration.

    The private key get decoded or decrypted into its origin byte
    representation. If the key is provided by a keystore, the password
    is first read in to decrypt the store. This function expects an
    earlier validation of the configuration and does not check if the
    parameters do actually exist. Anyways this is the place where the
    existence of the keystore and password file is verified.
    """

    private_key: dict = config["validator_private_key"]

    if "raw" in private_key:
        raw_key = private_key["raw"]
        raw_key_bytes = decode_hex(raw_key)
        return raw_key_bytes

    else:
        keystore_path = private_key["keystore_path"]
        keystore_password_path = private_key["keystore_password_path"]

        if not isfile(keystore_path) or not access(keystore_path, R_OK):
            raise ValueError(
                f"The keystore file does not exist or is not readable: '{keystore_path}'"
            )

        if not isfile(keystore_password_path) or not access(
            keystore_password_path, R_OK
        ):
            raise ValueError(
                f"The keystore password file does not exist or is not readable: '{keystore_password_path}'"
            )

        with open(keystore_password_path, "r") as password_file:
            password = password_file.readline().strip()

        try:
            return extract_key_from_keyfile(keystore_path, password.encode("utf-8"))

        except ValueError:
            raise ValueError(
                f"Could not decrypt keystore. Please make sure the password is correct."
            )
