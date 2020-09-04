import filecmp
import functools
import os
import shutil
import subprocess
import time
from textwrap import fill
from typing import List

import click
import pkg_resources

from quickstart.constants import SHARED_CHAIN_SPEC_PATH
from quickstart.utils import (
    is_bridge_prepared,
    is_netstats_prepared,
    is_validator_account_prepared,
    show_file_diff,
)
from quickstart.validator_account import get_author_address, get_validator_address

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
DOCKER_COMPOSE_OVERRIDE_FILE_NAME = "docker-compose.override.yaml"

README_PATH = "readme.txt"
README_TEXT = "\n".join(
    [
        "# Readme",
        "",
        "You can check which services are running with `docker-compose ps`.",
        "You can use `docker-compose down` to shut the services down or `docker-compose up` to start them. "
        "Beware that if you use `docker-compose up`, every service will be started even when they were not set up by the quickstart. "
        "You can also stop individual services for example `docker-compose stop watchtower`.",
        "For more information see the docker-compose documentation via `docker-compose --help` or online at https://docs.docker.com/compose/. "
        "You can also check the docker documentation via `docker --help` or online at https://docs.docker.com/engine/reference/commandline/docker/",
    ]
)


def setup_interactivaly(base_dir, docker_compose_file, expose_node_ports):
    create_docker_readme(base_dir)

    existing_docker_compose_file = os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME)
    if does_docker_compose_file_exist(base_dir) and not filecmp.cmp(
        existing_docker_compose_file, docker_compose_file
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

    existing_override_file = os.path.join(base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME)
    default_override_file = get_docker_compose_override_file()
    if expose_node_ports:
        if does_docker_compose_override_file_exist(base_dir) and not filecmp.cmp(
            existing_override_file, default_override_file
        ):
            while True:
                choice = click.prompt(
                    fill(
                        "You already seem to have a docker compose override file. "
                        "If you did not change it, you can safely overwrite it."
                        "Overwrite with default (1), keep own (2), or show diff (3)?"
                    )
                    + "\n",
                    type=click.Choice(("1", "2", "3")),
                    show_choices=False,
                )

                if choice == "1":
                    copy_default_docker_override_file(base_dir=base_dir)
                    break
                elif choice == "2":
                    # Nothing to do
                    break
                elif choice == "3":
                    show_override_diff(base_dir=base_dir)
                else:
                    assert False, "unreachable"
        else:
            copy_default_docker_override_file(base_dir=base_dir)
    else:
        if does_docker_compose_override_file_exist(base_dir) and filecmp.cmp(
            existing_override_file, default_override_file
        ):
            while True:
                click.secho(
                    fill(
                        "You already seem to have a default docker compose override file. "
                        "This file is responsible for exposing the ports of the node to the local machine."
                        "Do you want to keep the file and run the home node with exposed ports or remove it?"
                    )
                    + "\n",
                    fg="red",
                )
                choice = click.prompt(
                    fill("Keep the file (1) or remove it (2)?") + "\n",
                    type=click.Choice(("1", "2")),
                    show_choices=False,
                )

                if choice == "1":
                    # nothing to do
                    break
                elif choice == "2":
                    delete_docker_override_file(base_dir)
                    break
                else:
                    assert False, "unreachable"


def create_docker_readme(base_dir):
    if not os.path.isfile(os.path.join(base_dir, README_PATH)):
        with open(os.path.join(base_dir, README_PATH), "x") as f:
            f.write(README_TEXT)


def update_and_start(
    *, base_dir, host_base_dir, project_name, start_foreign_node
) -> None:
    if not does_docker_compose_file_exist(base_dir):
        raise click.ClickException(
            "\n"
            + fill(
                "Expecting a docker-compose configuration file at the current directory "
                f"with name '{DOCKER_COMPOSE_FILE_NAME}'"
            )
        )

    main_docker_service_names = ["home-node", "watchtower"]
    optional_docker_service_names = get_optional_docker_service_names(
        base_dir, start_foreign_node
    )
    all_docker_service_names = (
        main_docker_service_names + optional_docker_service_names + ["tlbc-monitor"]
    )

    env_variables = {"COMPOSE_PROJECT_NAME": project_name}
    if is_validator_account_prepared(base_dir):
        env_variables = {
            **env_variables,
            "ADDRESS_ARG": f"--address {get_validator_address(base_dir)}",
            "AUTHOR_ARG": f"--author {get_author_address(base_dir)}",
            "ROLE": "validator",
        }
        click.echo("\nNode will run as a validator")
    else:
        env_variables = {**env_variables, "ROLE": "observer"}
        click.echo("\nNode will run as a non-validator")

    with open(os.path.join(base_dir, ".env"), mode="w") as env_file:
        env_file.writelines(
            f"{key}={value}\n" for (key, value) in env_variables.items()
        )

    runtime_env_variables = {**os.environ, **env_variables}

    if host_base_dir is not None:
        runtime_env_variables["HOST_BASE_DIR"] = host_base_dir

    run_kwargs = {
        "env": runtime_env_variables,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "universal_newlines": True,
    }

    docker_compose_file_path = os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME)
    docker_compose_path_option = ["-f", docker_compose_file_path]

    if does_docker_compose_override_file_exist(base_dir):
        docker_compose_override_file_path = os.path.join(
            base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME
        )
        docker_compose_path_option += ["-f", docker_compose_override_file_path]

    try:
        click.echo("Shutting down possibly remaining docker services first...")
        subprocess.run(
            ["docker-compose", *docker_compose_path_option, "down"],
            check=True,
            **run_kwargs,
        )

        for container_name in LEGACY_CONTAINER_NAMES:
            # use check=False as docker stop and docker rm fail if the container does not exist
            subprocess.run(
                ["docker", "stop", container_name], check=False, **run_kwargs
            )
            subprocess.run(["docker", "rm", container_name], check=False, **run_kwargs)

        click.echo("Pulling recent Docker image versions...")
        subprocess.run(
            ["docker-compose", *docker_compose_path_option, "pull"]
            + all_docker_service_names,
            check=True,
            **run_kwargs,
        )

        click.echo("Starting Docker services...")
        subprocess.run(
            ["docker-compose", *docker_compose_path_option, "up", "--no-start"],
            check=True,
            **run_kwargs,
        )
        subprocess.run(
            ["docker-compose", *docker_compose_path_option, "start"]
            + main_docker_service_names
            + optional_docker_service_names,
            check=True,
            **run_kwargs,
        )

        wait_for_chain_spec(base_dir)

        subprocess.run(
            ["docker-compose", *docker_compose_path_option, "start", "tlbc-monitor"],
            check=True,
            **run_kwargs,
        )

    except subprocess.CalledProcessError as called_process_error:
        raise click.ClickException(
            "\n".join(
                (
                    fill(
                        f"Command {' '.join(called_process_error.cmd)} failed with exit code "
                        f"{called_process_error.returncode}."
                    ),
                    fill("Captured stderr:"),
                    fill(f"{called_process_error.stderr}"),
                )
            )
        )

    click.echo(
        "\n".join(
            [
                "",
                "Congratulations!",
                "All services are running as docker container in the background.",
                f"The configuration has been written to the sub-folder: {base_dir}",
            ]
        )
    )


def wait_for_chain_spec(base_dir) -> None:
    while not os.path.exists(os.path.join(base_dir, SHARED_CHAIN_SPEC_PATH)):
        time.sleep(1)


def get_optional_docker_service_names(base_dir, start_foreign_node) -> List[str]:
    docker_service_names = []

    if is_netstats_prepared(base_dir=base_dir):
        docker_service_names.append("netstats-client")

    if is_bridge_prepared(base_dir=base_dir):
        docker_service_names.append("bridge-client")
        if start_foreign_node:
            docker_service_names.append("foreign-node")

    return docker_service_names


def does_docker_compose_file_exist(base_dir):
    return os.path.isfile(os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME))


def does_docker_compose_override_file_exist(base_dir):
    return os.path.isfile(os.path.join(base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME))


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


def copy_default_docker_override_file(base_dir):
    docker_compose_override_file = get_docker_compose_override_file()
    if not os.path.isfile(docker_compose_override_file):
        raise click.ClickException(
            "\n"
            + fill(
                f"Expecting a docker-compose override configuration file at {docker_compose_override_file}"
            )
        )
    shutil.copyfile(
        docker_compose_override_file,
        os.path.join(base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME),
    )


def delete_docker_override_file(base_dir):
    path = os.path.join(base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME)
    if not os.path.isfile(path):
        raise ValueError(f"Expected to have a file at path: {path}")
    os.remove(path)


def show_diff(base_dir, docker_compose_file):
    show_file_diff(
        os.path.join(base_dir, DOCKER_COMPOSE_FILE_NAME),
        docker_compose_file,
        file_name=DOCKER_COMPOSE_FILE_NAME,
    )


def show_override_diff(base_dir):
    show_file_diff(
        os.path.join(base_dir, DOCKER_COMPOSE_OVERRIDE_FILE_NAME),
        get_docker_compose_override_file(),
        file_name=DOCKER_COMPOSE_OVERRIDE_FILE_NAME,
    )


def get_docker_compose_override_file():
    return functools.partial(
        pkg_resources.resource_filename,
        __name__,
        f"configs/{DOCKER_COMPOSE_OVERRIDE_FILE_NAME}",
    )()
