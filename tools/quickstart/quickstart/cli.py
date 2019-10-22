import functools
from textwrap import fill

import click
import pkg_resources

from quickstart import bridge, docker, monitor, netstats, validator_account

DEFAULT_CONFIGS = ["laika"]
LAIKA, = DEFAULT_CONFIGS

LAIKA_DOCKER_COMPOSE_FILE = "laika-docker-compose.yaml"
LAIKA_BRIDGE_CONFIG_FILE = "laika-bridge-config.toml"
LAIKA_NETSTATS_SERVER_BASE_URL = "https://laikanetstats.trustlines.foundation/"


def config_file_getter(filename):
    return functools.partial(
        pkg_resources.resource_filename, __name__, f"configs/{filename}"
    )


class DefaultPathType(click.Path):
    def __init__(self, default_path_lookups, *args, **kwargs):
        """
        Like the click path type, but additionally accepts a mapping for predefined paths
        :param default_path_lookups: mapping from template name to lookup function
        :param args: args for click.Path
        :param kwargs: kwargs for click.Path
        """
        super().__init__(*args, **kwargs)

        self.default_path_lookups = default_path_lookups

    def convert(self, value, param, ctx):
        if value in self.default_path_lookups:
            value = self.default_path_lookups[value]()

        return super().convert(value, param, ctx)


host_base_dir_option = click.option(
    "--host-base-dir",
    help=(
        "Absolute path to use for docker volumes (only relevant when run from inside a docker "
        "container itself)"
    ),
    type=click.Path(),  # Can not check for exist, because path is on host
    default=None,
)


@click.group()
def main():
    """Script to guide you through the quick setup of a Trustlines blockchain node."""
    pass


@main.command()
@click.option(
    "--docker-compose-file",
    help=f"Path to the docker compose file to use, or '{LAIKA}' for the default Laika docker compose file.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={LAIKA: config_file_getter(LAIKA_DOCKER_COMPOSE_FILE)},
    ),
    required=True,
)
@click.option(
    "--bridge-config",
    help=f"Path to the bridge configuration, or '{LAIKA}' for the default Laika configuration.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={LAIKA: config_file_getter(LAIKA_BRIDGE_CONFIG_FILE)},
    ),
    required=True,
)
@click.option(
    "--netstats-url", help="URL to netstats server", default=None, metavar="URL"
)
@click.option(
    "--project-name",
    help="The project name. This will be used to namespace the docker containers (<project-name>_<service-name>)",
    default="trustlines",
    show_default=True,
)
@click.option(
    "-d",
    "--base-dir",
    help="Path where everything is installed into",
    type=click.Path(file_okay=False),
    default="trustlines",
    show_default=True,
)
@host_base_dir_option
def custom(
    host_base_dir,
    docker_compose_file,
    base_dir,
    project_name,
    bridge_config,
    netstats_url,
):
    """
    Setup with custom settings.

    Setup all the necessary services for the custom node setup.
    """

    if netstats_url == LAIKA:
        netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL

    run(
        "custom Trustlines blockchain node",
        base_dir=base_dir,
        bridge_config_file=bridge_config,
        docker_compose_file=docker_compose_file,
        netstats_url=netstats_url,
        project_name=project_name,
        host_base_dir=host_base_dir,
    )


@main.command()
@click.option(
    "--project-name",
    help="The project name. This will be used to namespace the docker containers (<project-name>_<service-name>)",
    default="trustlines",
    show_default=True,
)
@click.option(
    "-d",
    "--base-dir",
    help="Path where everything is installed into",
    type=click.Path(file_okay=False),
    default="trustlines",
    show_default=True,
)
@host_base_dir_option
def laika(host_base_dir, project_name, base_dir):
    """
    Setup with Laika settings.

    Setup the services for the Laika testnet network with default settings.
    """
    docker_compose_file = config_file_getter(LAIKA_DOCKER_COMPOSE_FILE)()
    bridge_config_file = config_file_getter(LAIKA_BRIDGE_CONFIG_FILE)()
    netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL
    run(
        "Laika testnet node",
        bridge_config_file=bridge_config_file,
        docker_compose_file=docker_compose_file,
        netstats_url=netstats_url,
        host_base_dir=host_base_dir,
        project_name=project_name,
        base_dir=base_dir,
    )


def run(
    setup_name,
    *,
    bridge_config_file,
    docker_compose_file,
    base_dir,
    project_name,
    netstats_url=None,
    host_base_dir=None,
):
    click.echo(
        "\n".join(
            (
                fill(
                    f"This script will guide you through the setup of a {setup_name} as well as a few "
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
    bridge.setup_interactively(base_dir=base_dir, bridge_config_file=bridge_config_file)
    netstats.setup_interactively(base_dir=base_dir, netstats_url=netstats_url)
    docker.setup_interactivaly(
        base_dir=base_dir, docker_compose_file=docker_compose_file
    )
    docker.update_and_start(
        base_dir=base_dir, host_base_dir=host_base_dir, project_name=project_name
    )


if __name__ == "__main__":
    main()
