import os
import shutil
from pathlib import Path
from textwrap import fill

import click

from quickstart.constants import BRIDGE_CONFIG_FILE_EXTERNAL, BRIDGE_DOCUMENTATION_URL
from quickstart.utils import is_bridge_prepared, is_validator_account_prepared


def setup_interactively(base_dir, bridge_config_file) -> None:
    if is_bridge_prepared(base_dir):
        click.echo("\nThe bridge client has already been set up.")
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
        Path(os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL)).touch()
        return

    shutil.copyfile(
        bridge_config_file, os.path.join(base_dir, BRIDGE_CONFIG_FILE_EXTERNAL)
    )
    click.echo("Bridge client setup complete.")
