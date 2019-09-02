import os
import subprocess
from typing import List

import click

from quickstart.utils import (
    is_bridge_prepared,
    is_netstats_prepared,
    is_validator_account_prepared,
)
from quickstart.validator_account import get_validator_address


def update_and_start() -> None:
    if not is_validator_account_prepared():
        raise click.ClickException(
            "Can not start docker services without a setup validator account!"
        )

    if not os.path.isfile("docker-compose.yaml") and not os.path.isfile(
        "docker-compose.yml"
    ):
        raise click.ClickException(
            "Expecting a docker-compose configuration file at the current directory "
            "with a standard name. ('docker-compose.yaml' or 'docker-compose.yml')"
        )

    docker_service_names = get_docker_service_names()
    docker_environment_variables = {"VALIDATOR_ADDRESS": get_validator_address()}

    try:
        click.echo("\nShut down possibly remaining docker services...")
        subprocess.run(["docker-compose", "down"], env=docker_environment_variables)

        click.echo("\nPull recent Docker image versions...")
        subprocess.run(
            ["docker-compose", "pull"] + docker_service_names,
            env=docker_environment_variables,
            check=True,
        )

        click.echo("\nStart Docker services...")
        subprocess.run(
            ["docker-compose", "up", "--no-start"],
            env=docker_environment_variables,
            check=True,
        )
        subprocess.run(
            ["docker-compose", "start"] + docker_service_names,
            env=docker_environment_variables,
            check=True,
            capture_output=True,
        )

    except subprocess.CalledProcessError:
        raise click.ClickException(
            "Something went wrong while interacting with Docker."
        )

    click.echo("\nAll services are running. Congratulations!")


def get_docker_service_names() -> List[str]:
    docker_service_names = ["trustlines-node", "watchtower"]
    if is_netstats_prepared():
        docker_service_names.append("netstats-client")

    if is_bridge_prepared():
        docker_service_names.append("bridge-client")
        docker_service_names.append("mainnet-node")

    return docker_service_names
