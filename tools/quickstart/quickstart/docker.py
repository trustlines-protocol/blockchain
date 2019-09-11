import os
import subprocess
from textwrap import fill
from typing import List

import click

from quickstart.utils import (
    is_bridge_prepared,
    is_netstats_prepared,
    is_validator_account_prepared,
)
from quickstart.validator_account import get_validator_address

# List of docker container names to stop and remove on startup in addition to the ones defined in
# the docker compose file (for backward compatibility)
LEGACY_CONTAINER_NAMES = ["watchtower-testnet", "trustlines-testnet"]


def update_and_start(host_base_dir: str) -> None:
    if not os.path.isfile("docker-compose.yaml") and not os.path.isfile(
        "docker-compose.yml"
    ):
        raise click.ClickException(
            fill(
                "Expecting a docker-compose configuration file at the current directory "
                "with a standard name. ('docker-compose.yaml' or 'docker-compose.yml')"
            )
        )

    docker_service_names = get_docker_service_names()
    base_docker_environment_variables = {**os.environ, "HOST_BASE_DIR": host_base_dir}

    if is_validator_account_prepared():
        docker_environment_variables = {
            **base_docker_environment_variables,
            "VALIDATOR_ADDRESS": get_validator_address(),
            "ROLE": "validator",
        }
    else:
        docker_environment_variables = {
            **base_docker_environment_variables,
            "VALIDATOR_ADDRESS": "",
            "ROLE": "observer",
        }

    try:
        click.echo("\nShutting down possibly remaining docker services...")
        subprocess.run(["docker-compose", "down"], env=docker_environment_variables)
        for container_name in LEGACY_CONTAINER_NAMES:
            subprocess.run(
                ["docker", "stop", container_name], env=docker_environment_variables
            )
            subprocess.run(
                ["docker", "rm", container_name], env=docker_environment_variables
            )

        click.echo("\nPulling recent Docker image versions...")
        subprocess.run(
            ["docker-compose", "pull"] + docker_service_names,
            env=docker_environment_variables,
            check=True,
        )

        click.echo("\nStarting Docker services...")
        subprocess.run(
            ["docker-compose", "up", "--no-start"],
            env=docker_environment_variables,
            check=True,
        )
        subprocess.run(
            ["docker-compose", "start"] + docker_service_names,
            env=docker_environment_variables,
            check=True,
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
