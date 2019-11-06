import filecmp
import os
import shutil
from pathlib import Path
from textwrap import fill

import click
import toml
from requests.exceptions import ConnectionError, HTTPError
from web3 import HTTPProvider, Web3

from quickstart.constants import BRIDGE_CONFIG_FILE_EXTERNAL, BRIDGE_DOCUMENTATION_URL
from quickstart.utils import (
    file_hash,
    is_bridge_prepared,
    is_validator_account_prepared,
    show_file_diff,
)

# List of hashes of former default bridge configs
LEGACY_CONFIG_HASHES = ["15dda4731c857ff978141e583c5e995727fb0284"]


def setup_interactively(base_dir, bridge_config_file, foreign_chain_name) -> None:
    user_file = os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL)
    if is_bridge_prepared(base_dir):
        click.echo("\nThe bridge client has already been set up.")
        if file_hash(user_file) in LEGACY_CONFIG_HASHES:
            # Override former config files without asking
            copy_default_bridge_config(base_dir, bridge_config_file)
        elif filecmp.cmp(user_file, bridge_config_file):
            # same file, so nothing to do
            pass
        else:
            # Custom changes
            _show_file_override_dialog(base_dir, bridge_config_file)
        return

    if not is_validator_account_prepared(base_dir):
        click.echo("\nNo bridge node will be set up when running as a non-validator.")
        return

    click.echo(
        "\n".join(
            (
                "",
                fill(
                    "As a validator of the Trustlines blockchain, you are required to run a "
                    "bridge node. Checkout the following link for more information:"
                ),
                BRIDGE_DOCUMENTATION_URL,
                "",
            )
        )
    )
    if not click.confirm(
        "Do you want to set up a bridge node now? (recommended)", default=True
    ):
        # Necessary to make docker-compose not complain about it.
        Path(user_file).touch()
        return

    choice = click.prompt(
        fill(
            f"The bridge needs a a connection to a(n) {foreign_chain_name} node.\n"
            f"Do you want to run a light node (1) (default) "
            f"or do you already have a node running and want to connect via JSON rpc (2) ?"
        )
        + "\n",
        type=click.Choice(("1", "2")),
        show_choices=False,
        default="1",
        show_default=False,
    )
    if choice == "1":
        copy_default_bridge_config(base_dir, bridge_config_file)
        assert is_bridge_using_template_json_rpc_url(base_dir, bridge_config_file)
    elif choice == "2":
        url = read_json_rpc_url(bridge_config_file)
        # We want to ask for the URL before we copy the default config in case the user exits while entering the url
        # and wishes to restart the process
        copy_default_bridge_config(base_dir, bridge_config_file)
        change_json_rpc_url(user_file, url)
    else:
        assert False, "unreachable"

    click.echo("Bridge client setup complete.")


def copy_default_bridge_config(base_dir, bridge_config_file):
    shutil.copyfile(
        bridge_config_file, os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL)
    )


def _show_file_override_dialog(base_dir, bridge_config_file):
    while True:
        choice = click.prompt(
            fill(
                "You already seem to have a bridge config file. "
                "If you did not change it, you can safely override it.\n"
                "Override with default (1), keep own (2), or show diff (3) ?"
            )
            + "\n",
            type=click.Choice(("1", "2", "3")),
            show_choices=False,
        )

        if choice == "1":
            copy_default_bridge_config(base_dir, bridge_config_file)
            break
        elif choice == "2":
            # Nothing to do
            break
        elif choice == "3":
            show_file_diff(
                os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL),
                bridge_config_file,
                file_name=BRIDGE_CONFIG_FILE_EXTERNAL,
            )
        else:
            assert False, "unreachable"


def read_json_rpc_url(bridge_config_file):
    while True:
        url = click.prompt("JSON RPC url")
        # If the given url matches the one in the template, we cannot gracefully handle
        # whether we should run the foreign node ourselves
        if is_default_json_url(bridge_config_file, url):
            click.echo(
                fill(
                    "The given url clashes with the default rpc url. "
                    "Please enter a different url"
                )
            )
            continue
        try:
            Web3(HTTPProvider(url)).eth.blockNumber
            break
        except (ConnectionError, HTTPError, ValueError) as e:
            click.echo("Error: \n" + fill(str(e)))
            choice = click.confirm(
                f"We could not properly connect to the given url\n"
                f"Do you want to proceed anyways?\n",
                default=False,
            )
            if choice:
                break
            else:
                continue
    return url


def is_default_json_url(template_path, url):
    config = toml.load(template_path)
    return url == config["foreign_chain"]["rpc_url"]


def change_json_rpc_url(config_file, url):
    config = toml.load(config_file)
    config["foreign_chain"]["rpc_url"] = url

    with open(config_file, mode="w") as file:
        toml.dump(config, file)


def is_bridge_using_template_json_rpc_url(base_dir, template_path):
    user_config = toml.load(os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL))
    return is_default_json_url(template_path, user_config["foreign_chain"]["rpc_url"])
