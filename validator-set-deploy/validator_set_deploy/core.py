from eth_keyfile import extract_key_from_keyfile


def decrypt_private_key(keystore_path: str, password: str) -> bytes:
    return extract_key_from_keyfile(keystore_path, password.encode("utf-8"))


def build_transaction_options(*, gas, gas_price, nonce):

    transaction_options = {}

    if gas is not None:
        transaction_options["gas"] = gas
    if gas_price is not None:
        transaction_options["gasPrice"] = gas_price
    if nonce is not None:
        transaction_options["nonce"] = nonce

    return transaction_options
