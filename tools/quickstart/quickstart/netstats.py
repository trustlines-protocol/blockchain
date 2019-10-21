import os
from pathlib import Path
from textwrap import fill

import click
import requests

from quickstart.constants import NETSTATS_ENV_FILE_PATH, NETSTATS_SERVER_BASE_URL
from quickstart.utils import is_netstats_prepared

ENV_FILE_TEMPLATE = """\
WS_USER={username}
WS_PASSWORD={password}
INSTANCE_NAME={instance_name}
# HIDE_VALIDATOR_STATUS=false
"""


def setup_interactively(base_dir) -> None:
    if is_netstats_prepared(base_dir):
        click.echo("\nThe netstats client has already been set up.")
        return

    click.echo(
        "\n".join(
            (
                "",
                fill(
                    "This script can set up a client that reports to the netstats server running at"
                ),
                NETSTATS_SERVER_BASE_URL,
                "This helps the community to observe the state of the network.",
                "",
                fill(
                    "You will need credentials to do that. Please feel free to send an email to"
                ),
                "'netstats@trustlines.foundation'",
                fill(
                    "to receive yours if you don't have any yet and would like to participate."
                ),
                "",
            )
        )
    )

    if not click.confirm(
        fill(
            "Have you already received credentials and do you want to set up the netstats client?"
        )
    ):
        # Necessary to make docker-compose not complaining about it.
        Path(os.path.join(base_dir, NETSTATS_ENV_FILE_PATH)).touch()
        return

    while True:
        username = click.prompt("Username")
        password = click.prompt("Password", hide_input=True)

        if check_credentials(username, password):
            click.echo("The provided credentials are valid.")
            break

        else:
            click.echo(
                "\n"
                + "\n".join(
                    (
                        "The provided credentials could not be verified.",
                        fill(
                            "Please try entering them and make sure you are connected to the internet."
                        ),
                    )
                )
            )

    click.echo(
        "\n".join(
            (
                "Please enter a name to identify your instance on the website.",
                fill(
                    "You are free to choose any name you like. Note that the name will be publicly visible."
                ),
            )
        )
    )

    instance_name = click.prompt("Instance name")

    with open(os.path.join(base_dir, NETSTATS_ENV_FILE_PATH), "w") as env_file:
        env_file.write(
            ENV_FILE_TEMPLATE.format(
                username=username, password=password, instance_name=instance_name
            )
        )

    click.echo("Netstats client setup complete.\n")


def check_credentials(username: str, password: str) -> bool:
    url = f"{NETSTATS_SERVER_BASE_URL}/check"
    response = requests.get(url, auth=(username, password), timeout=10.0)
    return response.status_code == 200
