from pathlib import Path

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


def setup_interactively() -> None:
    if is_netstats_prepared():
        click.echo("You have already a setup the netstats client.\n")
        return

    click.echo(
        "\nWe can setup a client that reports to the netstats server running at\n"
        f"{NETSTATS_SERVER_BASE_URL}\nYou will need credentials to do that.\n"
    )

    if not click.confirm(
        "Did you already receive credentials and want to setup the netstats client?"
    ):
        # Necessary to make docker-compose not complaining about it.
        Path(NETSTATS_ENV_FILE_PATH).touch()
        return

    while True:
        username = click.prompt("Username")
        password = click.prompt("Password", hide_input=True)

        if check_credentials(username, password):
            click.echo("The provided credentials do work.")
            break

        else:
            click.echo(
                "The provided credentials do not work. Please try to enter them again."
            )

    click.echo(
        "Please enter an instance name now. You are free to choose any name you like."
    )

    instance_name = click.prompt("Instance name")

    with open(NETSTATS_ENV_FILE_PATH, "w") as env_file:
        env_file.write(
            ENV_FILE_TEMPLATE.format(
                username=username, password=password, instance_name=instance_name
            )
        )

    click.echo("Netstats client setup done\n")


def check_credentials(username: str, password: str) -> bool:
    url = f"{NETSTATS_SERVER_BASE_URL}/check"
    response = requests.get(url, auth=(username, password), timeout=10.0)
    return response.status_code == 200
