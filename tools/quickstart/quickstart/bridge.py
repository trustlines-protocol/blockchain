import filecmp
import os
import shutil
from pathlib import Path
from textwrap import fill

import click

from quickstart.constants import BRIDGE_CONFIG_FILE_EXTERNAL, BRIDGE_DOCUMENTATION_URL
from quickstart.utils import (
    file_hash,
    is_bridge_prepared,
    is_validator_account_prepared,
    show_file_diff,
)

# List of hashes of former default bridge configs
LEGACY_CONFIG_HASHES = ["15dda4731c857ff978141e583c5e995727fb0284"]


def setup_interactively(base_dir, bridge_config_file) -> None:
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
        click.echo("\nNo bridge node will be set up as running as a non-validator.")
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

    copy_default_bridge_config(base_dir, bridge_config_file)

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
