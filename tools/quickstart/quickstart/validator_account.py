import json
import os
from textwrap import fill

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


def setup_interactively(base_dir) -> None:
    if is_validator_account_prepared(base_dir):
        click.echo("\nA validator account has already been set up.")
        return
    if not prompt_setup_as_validator():
        return

    ensure_clean_setup()

    os.makedirs(os.path.join(base_dir, CONFIG_DIR), exist_ok=True)
    os.makedirs(os.path.join(base_dir, ENODE_DIR), exist_ok=True)
    os.makedirs(os.path.join(base_dir, DATABASE_DIR), exist_ok=True)

    choice = click.prompt(
        fill(
            "Validators need a private key. Do you want to import an existing JSON "
            "keystore (1), enter a raw private key (2), or generate a new key (3) ?"
        )
        + "\n",
        type=click.Choice(("1", "2", "3")),
        show_choices=False,
    )

    if choice == "1":
        import_keystore_file(base_dir)
    elif choice == "2":
        import_private_key(base_dir)
    elif choice == "3":
        generate_new_account(base_dir)
    else:
        assert False, "unreachable"

    click.echo("Validator account setup complete.")


def prompt_setup_as_validator():
    choice = click.prompt(
        "\nDo you want to set up a validator account (1) or run a regular node (2)?",
        type=click.Choice(("1", "2")),
        show_choices=False,
    )
    if choice == "1":
        return True
    elif choice == "2":
        return False
    else:
        assert False, "unreachable"


def import_keystore_file(base_dir) -> None:
    click.echo("Starting to import an existing keystore...")
    keystore_path = get_keystore_path()

    with open(keystore_path, "rb") as keystore_file:
        keyfile_dict = json.load(keystore_file)

    account, password = read_decryption_password(keyfile_dict)
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEYSTORE_FILE_PATH),
    )
    trustlines_files.store(account, password)


def import_private_key(base_dir) -> None:
    click.echo("Starting to import an existing raw private key...")
    private_key = read_private_key()
    account = Account.from_key(private_key)
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEYSTORE_FILE_PATH),
    )
    trustlines_files.store(account, password)


def generate_new_account(base_dir) -> None:
    click.echo("Starting to generate a new private key...")
    account = Account.create()
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEYSTORE_FILE_PATH),
    )
    trustlines_files.store(account, password)


def get_validator_address(base_dir) -> str:
    if not is_validator_account_prepared(base_dir):
        raise ValueError("Validator account is not prepared! Can not read its address.")

    with open(os.path.join(base_dir, ADDRESS_FILE_PATH), "r") as address_file:
        return address_file.read()
