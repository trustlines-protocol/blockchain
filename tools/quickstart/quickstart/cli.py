"""import private key or keystore file as parity account"""

import sys
import os
import re
import json
from eth_account import Account
import click


class TrustlinesFiles:
    def __init__(self, password_file, address_file, keystore_file):
        self.password_file = password_file
        self.address_file = address_file
        self.keystore_file = keystore_file

    def store(self, account, password):
        # Instead of just copying the file, we encrypt it again since the
        # file itself may use scrypt as key derivative function which
        # parity can't handle
        json_account = account.encrypt(password, kdf="pbkdf2")

        os.makedirs(os.path.dirname(os.path.abspath(self.keystore_file)), exist_ok=True)
        with open(self.keystore_file, "w") as f:
            f.write(json.dumps(json_account))

        with open(self.password_file, "w") as f:
            f.write(password)

        with open(self.address_file, "w") as f:
            f.write(account.address)


def is_wrong_password_error(err):
    return type(err) is ValueError and str(err) == "MAC mismatch"


def import_keystore_file(trustline_files, keystore_input_file):
    keyfile_dict = json.loads(open(keystore_input_file, "rb").read())

    while 1:
        password = click.prompt(text="Password", hide_input=True)
        try:
            account = Account.from_key(Account.decrypt(keyfile_dict, password))
            break
        except Exception as err:
            if is_wrong_password_error(err):
                click.echo("The password you entered is wrong. Please try again.")
            else:
                click.echo(f"Error: malformed keystore file: {repr(err)}")
                sys.exit(1)
    trustline_files.store(account, password)
    sys.exit(0)


def read_private_key():
    while 1:
        privkey = click.prompt(text="Private key (hex encodded)", hide_input=True)
        if re.fullmatch("[0-9a-fA-F]{64}", privkey):
            return privkey
        click.echo(
            "The private key muss be entered as hex encoded string. Please try again."
        )


def read_password():
    while 1:
        password = click.prompt(text="Password", hide_input=True)
        password2 = click.prompt(text="Password (repeat)", hide_input=True)
        if password == password2:
            return password
        click.echo("Passwords do not match. Please try again.")


def import_private_key(trustline_files):
    private_key = read_private_key()
    account = Account.from_key(private_key)
    click.echo(f"Read private key for address {account.address}")
    password = read_password()

    trustline_files.store(account, password)


def make_trustlines_files():
    password_file, address_file, keystore_file = sys.argv[1:4]
    return TrustlinesFiles(
        password_file=password_file,
        address_file=address_file,
        keystore_file=keystore_file,
    )


def qs_import_keystore_file():
    if len(sys.argv) != 5:
        click.echo(
            "Usage: qs-import-keystore-file PASSWORD_FILE ADDRESS_FILE KEYSTORE_FILE KEYSTORE_INPUT_FILE"
        )
        sys.exit(1)
    import_keystore_file(make_trustlines_files(), keystore_input_file=sys.argv[4])


def qs_import_private_key():
    if len(sys.argv) != 4:
        click.echo(
            "Usage: qs-import-private-key PASSWORD_FILE ADDRESS_FILE KEYSTORE_FILE"
        )
        sys.exit(1)

    import_private_key(make_trustlines_files())
