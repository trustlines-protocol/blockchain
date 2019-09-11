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

    run_kwargs = {
        "env": docker_environment_variables,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    try:
        click.echo("\nShutting down possibly remaining docker services...")
        subprocess.run(["docker-compose", "down"], check=True, **run_kwargs)
        for container_name in LEGACY_CONTAINER_NAMES:
            # use check=False as docker stop and docker rm fail if the container does not exist
            subprocess.run(
                ["docker", "stop", container_name], check=False, **run_kwargs
            )
            subprocess.run(["docker", "rm", container_name], check=False, **run_kwargs)

        click.echo("\nPulling recent Docker image versions...")
        subprocess.run(
            ["docker-compose", "pull"] + docker_service_names, check=True, **run_kwargs
        )

        click.echo("\nStarting Docker services...")
        subprocess.run(["docker-compose", "up", "--no-start"], check=True, **run_kwargs)
        subprocess.run(
            ["docker-compose", "start"] + docker_service_names, check=True, **run_kwargs
        )

    except subprocess.CalledProcessError as called_process_error:
        raise click.ClickException(
            "\n".join(
                (
                    fill(
                        f"Command {' '.join(called_process_error.cmd)} failed with exit code "
                        f"{called_process_error.returncode}."
                    ),
                )
            )
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
