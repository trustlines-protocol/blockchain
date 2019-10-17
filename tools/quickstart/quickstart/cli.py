from textwrap import fill

import click

from quickstart import bridge, docker, monitor, netstats, validator_account


@click.command()
@click.option(
    "--host-base-dir",
    help=(
        "absolute path to use for docker volumes (only relevant when run from inside a docker "
        "container itself)"
    ),
    type=click.Path(),  # Can not check for exist, because path is on host
    default=None,
)
@click.option(
    "--docker-compose-file",
    help="path to the docker compose file to use",
    type=click.Path(exists=True, dir_okay=False),
    default="docker-compose.yaml",
)
@click.option(
    "-d",
    "--base-dir",
    help="path where everything is installed into",
    type=click.Path(file_okay=False),
    default="trustlines",
)
@click.option("--project-name", help="project name", default="trustlines")
def main(host_base_dir, docker_compose_file, base_dir, project_name):
    click.echo(
        "\n".join(
            (
                fill(
                    "This script will guide you through the setup of a Laika testnet node as well as a few "
                    "additional services. Once it is complete, the components will run in the background as "
                    "docker containers."
                ),
                "",
                fill(
                    "It is safe to run this script multiple times. Already existing containers will be "
                    "restarted and no configuration will be overwritten. It is possible to enable "
                    "additional components that you have chosen not to configure in earlier runs."
                ),
            )
        )
    )

    validator_account.setup_interactively(base_dir=base_dir)
    monitor.setup_interactively(base_dir=base_dir)
    bridge.setup_interactively(base_dir=base_dir)
    netstats.setup_interactively(base_dir=base_dir)
    docker.setup_interactivaly(
        base_dir=base_dir, docker_compose_file=docker_compose_file
    )
    docker.update_and_start(
        base_dir=base_dir, host_base_dir=host_base_dir, project_name=project_name
    )


if __name__ == "__main__":
    main()
