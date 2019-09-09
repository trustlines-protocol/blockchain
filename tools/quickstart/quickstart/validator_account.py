import json
import os

import click
from eth_account import Account

from quickstart.constants import (
    ADDRESS_FILE_PATH,
    CONFIG_DIR,
    DATABASE_DIR,
    ENODE_DIR,
    KEYSTORE_FILE_PATH,
    PASSWORD_FILE_PATH,
)
from quickstart.utils import (
    TrustlinesFiles,
    ensure_clean_setup,
    get_keystore_path,
    is_validator_account_prepared,
    read_decryption_password,
    read_encryption_password,
    read_private_key,
)


def setup_interactively() -> None:
    if is_validator_account_prepared():
        click.echo("You have already set a validator node up.\n")
        return

    ensure_clean_setup()

    click.echo("This script will setup a validator node for the Laika testnet chain.\n")

    os.makedirs(CONFIG_DIR, exist_ok=True)
    os.makedirs(ENODE_DIR, exist_ok=True)
    os.makedirs(DATABASE_DIR, exist_ok=True)

    click.echo(
        "Validators need a private key. This script can either import an existing JSON "
        "keystore, import an existing raw private key, or it can create a new key.\n"
    )

    if click.confirm("Do you want to import an existing keystore?"):
        import_keystore_file()

    elif click.confirm("Do you want to import an existing raw private key?"):
        import_private_key()

    elif click.confirm("Do you want to generate a new account?"):
        generate_new_account()

    else:
        raise click.ClickException(
            "To setup a validator node, a private key is required. "
            "You need to select one of the previous options."
        )

    click.echo("Validator account setup complete.")


def import_keystore_file() -> None:
    click.echo("Starting to import an existing keystore...")
    keystore_path = get_keystore_path()

    with open(keystore_path, "rb") as keystore_file:
        keyfile_dict = json.load(keystore_file)

    account, password = read_decryption_password(keyfile_dict)
    trustlines_files = TrustlinesFiles(
        PASSWORD_FILE_PATH, ADDRESS_FILE_PATH, KEYSTORE_FILE_PATH
    )
    trustlines_files.store(account, password)


def import_private_key() -> None:
    click.echo("Starting to import an existing raw private key...")
    private_key = read_private_key()
    account = Account.from_key(private_key)
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        PASSWORD_FILE_PATH, ADDRESS_FILE_PATH, KEYSTORE_FILE_PATH
    )
    trustlines_files.store(account, password)


def generate_new_account() -> None:
    click.echo("Starting to generate a new private key...")
    account = Account.create()
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        PASSWORD_FILE_PATH, ADDRESS_FILE_PATH, KEYSTORE_FILE_PATH
    )
    trustlines_files.store(account, password)


def get_validator_address() -> str:
    if not is_validator_account_prepared():
        raise ValueError("Validator account is not prepared! Can not read its address.")

    with open(ADDRESS_FILE_PATH, "r") as address_file:
        return address_file.read()
