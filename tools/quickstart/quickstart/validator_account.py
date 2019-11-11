import glob
import json
import os
from textwrap import fill

import click
from eth_account import Account

from quickstart.constants import (
    ADDRESS_FILE_PATH,
    AUTHOR_ADDRESS_FILE_PATH,
    CONFIG_DIR,
    DATABASE_DIR,
    ENODE_DIR,
    KEY_DIR,
    KEYSTORE_FILE_NAME,
    LEGACY_KEYSTORE_FILE_NAME_PATTERN,
    PASSWORD_FILE_PATH,
)
from quickstart.utils import (
    TrustlinesFiles,
    ensure_clean_setup,
    get_keystore_path,
    is_author_address_prepared,
    is_validator_account_prepared,
    read_address,
    read_decryption_password,
    read_encryption_password,
    read_private_key,
)


def setup_interactively(base_dir, chain_dir) -> None:
    handle_legacy_validator_key_file(base_dir, chain_dir)

    if is_validator_account_prepared(base_dir):
        click.echo("A validator account has already been set up.")
        return

    make_required_dirs(base_dir, chain_dir)

    if not prompt_setup_as_validator():
        return

    ensure_clean_setup(base_dir, chain_dir)

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
        import_keystore_file(base_dir, chain_dir)
    elif choice == "2":
        import_private_key(base_dir, chain_dir)
    elif choice == "3":
        generate_new_account(base_dir, chain_dir)
    else:
        assert False, "unreachable"

    click.echo("Validator account setup complete.")


def make_required_dirs(base_dir, chain_dir):
    """Make the directory with which the quickstart could interact before parity makes them
    to have write access"""
    os.makedirs(os.path.join(base_dir, CONFIG_DIR), exist_ok=True)
    os.makedirs(os.path.join(base_dir, ENODE_DIR), exist_ok=True)
    os.makedirs(os.path.join(base_dir, DATABASE_DIR), exist_ok=True)
    os.makedirs(os.path.join(base_dir, KEY_DIR, chain_dir), exist_ok=True)


def setup_author_address(setup_name, base_dir):
    if is_author_address_prepared(base_dir):
        click.echo("\nAn author address has already been configured.")
        return

    if not is_validator_account_prepared(base_dir):
        click.echo("\nSkip reward account setup for non validating node.")
        return

    if click.confirm(
        "\n"
        + fill(
            "Do you want to receive your mining rewards to a dedicated account instead of your "
            "validator account? This would increase security of your funds (for more information, "
            "see https://github.com/trustlines-protocol/blockchain/blob/master/README.md)."
        )
    ):
        click.echo(f"Please enter a {setup_name} address you have full control over")
        address = read_address()

        path = os.path.join(base_dir, AUTHOR_ADDRESS_FILE_PATH)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "x") as f:
            f.write(address)


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


def import_keystore_file(base_dir, chain_dir) -> None:
    click.echo("Starting to import an existing keystore...")
    keystore_path = get_keystore_path()

    with open(keystore_path, "rb") as keystore_file:
        keyfile_dict = json.load(keystore_file)

    account, password = read_decryption_password(keyfile_dict)
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEY_DIR, chain_dir, KEYSTORE_FILE_NAME),
    )
    trustlines_files.store(account, password)


def import_private_key(base_dir, chain_dir) -> None:
    click.echo("Starting to import an existing raw private key...")
    private_key = read_private_key()
    account = Account.from_key(private_key)
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEY_DIR, chain_dir, KEYSTORE_FILE_NAME),
    )
    trustlines_files.store(account, password)


def generate_new_account(base_dir, chain_dir) -> None:
    click.echo("Starting to generate a new private key...")
    account = Account.create()
    password = read_encryption_password()
    trustlines_files = TrustlinesFiles(
        os.path.join(base_dir, PASSWORD_FILE_PATH),
        os.path.join(base_dir, ADDRESS_FILE_PATH),
        os.path.join(base_dir, KEY_DIR, chain_dir, KEYSTORE_FILE_NAME),
    )
    trustlines_files.store(account, password)


def get_validator_address(base_dir) -> str:
    if not is_validator_account_prepared(base_dir):
        raise ValueError("Validator account is not prepared! Can not read its address.")

    with open(os.path.join(base_dir, ADDRESS_FILE_PATH), "r") as address_file:
        return address_file.read()


def get_author_address(base_dir) -> str:
    if not is_validator_account_prepared(base_dir):
        raise ValueError("Validator account is not prepared! Can not read its address.")

    try:
        with open(
            os.path.join(base_dir, AUTHOR_ADDRESS_FILE_PATH), "r"
        ) as author_address_file:
            return author_address_file.read()
    except FileNotFoundError:
        return get_validator_address(base_dir)


def handle_legacy_validator_key_file(base_dir, chain_dir):
    legacy_key_file_paths = legacy_validator_key_paths(base_dir, chain_dir)
    key_file_paths = legacy_key_file_paths.copy()
    if validator_key_file_exists(base_dir, chain_dir):
        key_file_paths.append(validator_key_file_path(base_dir, chain_dir))

    if len(key_file_paths) > 1:
        error_message = fill(
            f"There are multiple files that correspond to validator keys: {key_file_paths}. "
            f"Please make sure there is at most one key file in {os.path.join(base_dir, KEY_DIR, chain_dir)} "
            f"and restart the quickstart."
        )
        raise click.exceptions.UsageError(error_message)
    elif len(legacy_key_file_paths) == 1:
        try:
            rename_legacy_key_file(base_dir, chain_dir, key_file_paths[0])
        except PermissionError:
            error_message = fill(
                f"The validator key file {key_file_paths[0]} cannot be accessed, "
                f"please change the permissions of the file."
            )
            raise click.exceptions.UsageError(error_message)


def validator_key_file_exists(base_dir, chain_dir):
    return os.path.isfile(validator_key_file_path(base_dir, chain_dir))


def validator_key_file_path(base_dir, chain_dir):
    return os.path.join(base_dir, KEY_DIR, chain_dir, KEYSTORE_FILE_NAME)


def legacy_validator_key_paths(base_dir, chain_dir):
    return glob.glob(
        os.path.join(base_dir, KEY_DIR, chain_dir, LEGACY_KEYSTORE_FILE_NAME_PATTERN)
    )


def rename_legacy_key_file(base_dir, chain_dir, legacy_key_file_path):
    os.rename(legacy_key_file_path, validator_key_file_path(base_dir, chain_dir))
