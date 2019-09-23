import os
import subprocess
import time
from textwrap import fill
from typing import List

import click

from quickstart.constants import SHARED_CHAIN_SPEC_PATH
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
            "\n"
            + fill(
                "Expecting a docker-compose configuration file at the current directory "
                "with a standard name. ('docker-compose.yaml' or 'docker-compose.yml')"
            )
        )

    main_docker_service_names = ["trustlines-node", "watchtower"]
    optional_docker_service_names = get_optional_docker_service_names()
    all_docker_service_names = (
        main_docker_service_names + optional_docker_service_names + ["tlbc-monitor"]
    )

    base_docker_environment_variables = {**os.environ, "HOST_BASE_DIR": host_base_dir}
    if is_validator_account_prepared():
        docker_environment_variables = {
            **base_docker_environment_variables,
            "VALIDATOR_ADDRESS": get_validator_address(),
            "ROLE": "validator",
        }
        click.echo("\nNode will run as a validator")
    else:
        docker_environment_variables = {
            **base_docker_environment_variables,
            "VALIDATOR_ADDRESS": "",
            "ROLE": "observer",
        }
        click.echo("\nNode will run as a non-validator")

    run_kwargs = {
        "env": docker_environment_variables,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }

    try:
        click.echo("Shutting down possibly remaining docker services first...")
        subprocess.run(["docker-compose", "down"], check=True, **run_kwargs)
        for container_name in LEGACY_CONTAINER_NAMES:
            # use check=False as docker stop and docker rm fail if the container does not exist
            subprocess.run(
                ["docker", "stop", container_name], check=False, **run_kwargs
            )
            subprocess.run(["docker", "rm", container_name], check=False, **run_kwargs)

        click.echo("Pulling recent Docker image versions...")
        subprocess.run(
            ["docker-compose", "pull"] + all_docker_service_names,
            check=True,
            **run_kwargs,
        )

        click.echo("Starting Docker services...")
        subprocess.run(["docker-compose", "up", "--no-start"], check=True, **run_kwargs)
        subprocess.run(
            ["docker-compose", "start"]
            + main_docker_service_names
            + optional_docker_service_names,
            check=True,
            **run_kwargs,
        )

        wait_for_chain_spec()

        subprocess.run(
            ["docker-compose", "start", "tlbc-monitor"], check=True, **run_kwargs
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


def wait_for_chain_spec() -> None:
    while not os.path.exists(SHARED_CHAIN_SPEC_PATH):
        time.sleep(1)


def get_optional_docker_service_names() -> List[str]:
    docker_service_names = []

    if is_netstats_prepared():
        docker_service_names.append("netstats-client")

    if is_bridge_prepared():
        docker_service_names.append("bridge-client")
        docker_service_names.append("mainnet-node")

    return docker_service_names
