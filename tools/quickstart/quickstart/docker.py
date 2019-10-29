import filecmp
import os
import shutil
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
    show_file_diff,
)
from quickstart.validator_account import get_validator_address

# List of docker container names to stop and remove on startup in addition to the ones defined in
# the docker compose file (for backward compatibility)
LEGACY_CONTAINER_NAMES = [
    # malta quickstart version
    "watchtower-testnet",
    "trustlines-testnet",
    # intermediate quickstart versions
    "bridge-client",
    "tlbc-monitor",
    "mainnet.node",
    "laika-testnet.node",
    "netstats-client",
    "quickstart_bridge-client_1",
    "quickstart_tlbc-monitor_1",
    "quickstart_trustlines-node_1",
    "quickstart_mainnet-node_1",
    "quickstart_netstats-client_1",
    "quickstart_watchtower_1",
]
DOCKER_COMPOSE_FILE_NAME = "docker-compose.yaml"


def setup_interactivaly(base_dir, docker_compose_file):
    if does_docker_compose_file_exist(base_dir) and not filecmp.cmp(
        os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME), docker_compose_file
    ):
        while True:
            choice = click.prompt(
                fill(
                    "You already seem to have a docker compose file. "
                    "If you did not change it, you can safely overwrite it.\n"
                    "Overwrite with default (1), keep own (2), or show diff (3)?"
                )
                + "\n",
                type=click.Choice(("1", "2", "3")),
                show_choices=False,
            )

            if choice == "1":
                copy_default_docker_file(
                    base_dir=base_dir, docker_compose_file=docker_compose_file
                )
                break
            elif choice == "2":
                # Nothing to do
                break
            elif choice == "3":
                show_diff(base_dir=base_dir, docker_compose_file=docker_compose_file)
            else:
                assert False, "unreachable"
    else:
        copy_default_docker_file(
            base_dir=base_dir, docker_compose_file=docker_compose_file
        )


def update_and_start(*, base_dir, host_base_dir, project_name) -> None:
    if not does_docker_compose_file_exist(base_dir):
        raise click.ClickException(
            "\n"
            + fill(
                "Expecting a docker-compose configuration file at the current directory "
                f"with name '{DOCKER_COMPOSE_FILE_NAME}'"
            )
        )

    main_docker_service_names = ["home-node", "watchtower"]
    optional_docker_service_names = get_optional_docker_service_names(base_dir)
    all_docker_service_names = (
        main_docker_service_names + optional_docker_service_names + ["tlbc-monitor"]
    )

    default_env_vars = {"COMPOSE_PROJECT_NAME": project_name}
    if is_validator_account_prepared(base_dir):
        env_variables = {
            **default_env_vars,
            "VALIDATOR_ADDRESS": get_validator_address(base_dir),
            "ROLE": "validator",
        }
        click.echo("\nNode will run as a validator")
    else:
        env_variables = {
            **default_env_vars,
            "VALIDATOR_ADDRESS": "",
            "ROLE": "observer",
        }
        click.echo("\nNode will run as a non-validator")

    with open(os.path.join(base_dir, ".env"), mode="w") as env_file:
        env_file.writelines(
            f"{key}={value}\n" for (key, value) in env_variables.items()
        )

    runtime_env_variables = {
        **os.environ,
        **env_variables,
        "COMPOSE_FILE": os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME),
    }

    if host_base_dir is not None:
        runtime_env_variables["HOST_BASE_DIR"] = host_base_dir

    run_kwargs = {
        "env": runtime_env_variables,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "universal_newlines": True,
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

        wait_for_chain_spec(base_dir)

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
                    fill(f"Captured stderr:"),
                    fill(f"{called_process_error.stderr}"),
                )
            )
        )

    click.echo("\nAll services are running. Congratulations!")


def wait_for_chain_spec(base_dir) -> None:
    while not os.path.exists(os.path.join(base_dir, SHARED_CHAIN_SPEC_PATH)):
        time.sleep(1)


def get_optional_docker_service_names(base_dir) -> List[str]:
    docker_service_names = []

    if is_netstats_prepared(base_dir=base_dir):
        docker_service_names.append("netstats-client")

    if is_bridge_prepared(base_dir=base_dir):
        docker_service_names.append("bridge-client")
        docker_service_names.append("foreign-node")

    return docker_service_names


def does_docker_compose_file_exist(base_dir):
    return os.path.isfile(os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME))


def copy_default_docker_file(base_dir, docker_compose_file):
    if not os.path.isfile(docker_compose_file):
        raise click.ClickException(
            "\n"
            + fill(
                f"Expecting a docker-compose configuration file at {docker_compose_file}"
            )
        )
    shutil.copyfile(
        docker_compose_file, os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME)
    )


def show_diff(base_dir, docker_compose_file):
    show_file_diff(
        os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME),
        docker_compose_file,
        file_name=DOCKER_COMPOSE_FILE_NAME,
    )
