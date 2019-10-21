import functools
from textwrap import fill

import click
import pkg_resources

from quickstart import bridge, docker, monitor, netstats, validator_account

DEFAULT_CONFIGS = ["Laika"]
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


@click.command()
@click.option(
    "--config",
    "-c",
    help="Config to use. [Default: Laika]",
    type=click.Choice(DEFAULT_CONFIGS),
    default=None,
)
@click.option(
    "--host-base-dir",
    help=(
        "Absolute path to use for docker volumes (only relevant when run from inside a docker "
        "container itself)"
    ),
    type=click.Path(),  # Can not check for exist, because path is on host
    default=None,
)
@click.option(
    "--docker-compose-file",
    help="Path to the docker compose file to use, or laika for the default laika docker compose file.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={LAIKA: config_file_getter(LAIKA_DOCKER_COMPOSE_FILE)},
    ),
    default=None,
)
@click.option(
    "-d",
    "--base-dir",
    help="Path where everything is installed into",
    type=click.Path(file_okay=False),
    default="trustlines",
)
@click.option(
    "--bridge-config",
    help="Path to the bridge configuration, or laika for the default laika configuration.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={LAIKA: config_file_getter(LAIKA_BRIDGE_CONFIG_FILE)},
    ),
    default=None,
)
@click.option("--netstats-url", help="URL to netstats server", default=None)
@click.option(
    "--project-name",
    help="The project name. This will be used to namespace the docker containers (<project-name>_<service-name>)",
    default="trustlines",
)
def main(
    config,
    host_base_dir,
    docker_compose_file,
    base_dir,
    project_name,
    bridge_config,
    netstats_url,
):

    # if nothing is set, default to Laika
    if docker_compose_file is None and bridge_config is None and netstats_url is None:
        config = LAIKA

    if config is not None:
        if (
            docker_compose_file is not None
            or bridge_config is not None
            or netstats_url is not None
        ):
            raise click.BadOptionUsage(
                "--config",
                "When using the config option, you can not provide "
                "any of docker-compose-file, bridge-config or netstats-url.",
            )

        if config == LAIKA:
            docker_compose_file = config_file_getter(LAIKA_DOCKER_COMPOSE_FILE)()
            bridge_config = config_file_getter(LAIKA_BRIDGE_CONFIG_FILE)()
            netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL
        else:
            raise click.BadOptionUsage("config", f"Unexpected config option: {config}")
    else:
        if docker_compose_file is None:
            raise click.BadOptionUsage(
                "docker-compose-file",
                "You have to provide a docker compose file if you do not use the config option.",
            )
        if bridge_config is None:
            raise click.BadOptionUsage(
                "bridge-config",
                "You have to provide a bridge config file if you do not use the config option.",
            )
        if netstats_url is None:
            raise click.BadOptionUsage(
                "netstats-url",
                "You have to provide a netstats url if you do not use the config option.",
            )

    if netstats_url == LAIKA:
        netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL

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
    bridge.setup_interactively(base_dir=base_dir, bridge_config_file=bridge_config)
    netstats.setup_interactively(base_dir=base_dir, netstats_url=netstats_url)
    docker.setup_interactivaly(
        base_dir=base_dir, docker_compose_file=docker_compose_file
    )
    docker.update_and_start(
        base_dir=base_dir, host_base_dir=host_base_dir, project_name=project_name
    )


if __name__ == "__main__":
    main()
