import functools
from textwrap import fill

import click
import pkg_resources

from quickstart import bridge, docker, monitor, netstats, utils, validator_account

DEFAULT_CONFIGS = ["laika", "tlbc"]
LAIKA, TLBC = DEFAULT_CONFIGS

LAIKA_NETSTATS_SERVER_BASE_URL = "https://netstats.laika.trustlines.foundation/"
TLBC_NETSTATS_SERVER_BASE_URL = "https://netstats.tlbc.trustlines.foundation/"


def docker_compose_file_getter(config_name):
    return config_file_getter(config_name, "docker-compose.yaml")


def bridge_config_file_getter(config_name):
    return config_file_getter(config_name, "bridge-config.toml")


def config_file_getter(config_name, filename):
    return functools.partial(
        pkg_resources.resource_filename, __name__, f"configs/{config_name}/{filename}"
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


def project_name_option(**kwargs):
    return click.option(
        "--project-name",
        help="The project name. This will be used to namespace the docker containers (<project-name>_<service-name>)",
        show_default=True,
        **kwargs,
    )


def base_dir_option(**kwargs):
    return click.option(
        "-d",
        "--base-dir",
        help="Path where everything is installed into",
        type=click.Path(file_okay=False),
        show_default=True,
        **kwargs,
    )


def confirm_expose_ports(ctx, param, value):
    if value:
        click.secho(
            "Running the home node with exposed ports incurs risks.\n"
            "If the machine on which the node is ran exposes the\n"
            "ports itself the node will be queryable from outside.\n"
            "With the wrong settings, this means funds could be stolen.\n\n"
            "Only use this option if you know what you are doing.\n",
            "You can later change the exposed ports via the docker-compose.override.yaml file",
            fg="red",
        )
        if not click.confirm("Do you wish to continue?", default=False):
            ctx.abort()
    return value


expose_ports_option = click.option(
    "--expose-ports",
    "expose_node_ports",
    help="Expose the HTTP and WebSocket ports of the home node to the local machine on 8545 and 8546 respectively.",
    show_default=True,
    is_flag=True,
    default=False,
    callback=confirm_expose_ports,
)


@click.group()
def main():
    """Script to guide you through the quick setup of a Trustlines Blockchain node."""
    pass


@main.command()
@project_name_option(default="tlbc")
@base_dir_option(default="tlbc")
@host_base_dir_option
@expose_ports_option
def tlbc(host_base_dir, project_name, base_dir, expose_node_ports):
    """
    Setup with Trustlines Blockchain settings.

    Setup the services for the Trustlines Blockchain with default settings.
    """
    docker_compose_file = docker_compose_file_getter(TLBC)()
    bridge_config_file = bridge_config_file_getter(TLBC)()
    netstats_url = TLBC_NETSTATS_SERVER_BASE_URL
    run(
        "Trustlines Blockchain",
        foreign_chain_name="Ethereum mainnet",
        bridge_config_file=bridge_config_file,
        docker_compose_file=docker_compose_file,
        netstats_url=netstats_url,
        host_base_dir=host_base_dir,
        project_name=project_name,
        base_dir=base_dir,
        chain_dir="tlbc",
        expose_node_ports=expose_node_ports,
    )


@main.command()
@project_name_option(default="laika")
@base_dir_option(default="trustlines")  # for backwards compatibility
@host_base_dir_option
@expose_ports_option
def laika(host_base_dir, project_name, base_dir, expose_node_ports):
    """
    Setup with Laika settings.

    Setup the services for the Laika testnet network with default settings.
    """
    docker_compose_file = docker_compose_file_getter(LAIKA)()
    bridge_config_file = bridge_config_file_getter(LAIKA)()
    netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL
    run(
        "Laika Testnet",
        foreign_chain_name="Görli testnet",
        bridge_config_file=bridge_config_file,
        docker_compose_file=docker_compose_file,
        netstats_url=netstats_url,
        host_base_dir=host_base_dir,
        project_name=project_name,
        base_dir=base_dir,
        chain_dir="Trustlines",
        expose_node_ports=expose_node_ports,
    )


@main.command()
@click.option(
    "--docker-compose-file",
    help=f"Path to the docker compose file to use, or one of '{TLBC}', '{LAIKA}' for the default TLBC or Laika docker compose file.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={
            LAIKA: docker_compose_file_getter(LAIKA),
            TLBC: docker_compose_file_getter(TLBC),
        },
    ),
    required=True,
)
@click.option(
    "--bridge-config",
    help=f"Path to the bridge configuration, or one of '{TLBC}', '{LAIKA}' for the default TLBC or Laika bridge config.",
    type=DefaultPathType(
        exists=True,
        dir_okay=False,
        default_path_lookups={
            LAIKA: bridge_config_file_getter(LAIKA),
            TLBC: bridge_config_file_getter(TLBC),
        },
    ),
    required=True,
)
@click.option(
    "--netstats-url",
    help="URL to netstats server, or one of '{TLBC}', '{LAIKA}' for the default TLBC or Laika netstats server.",
    default=None,
    metavar="URL",
)
@click.option(
    "--chain-dir",
    help="The chain directory name as specified in the chain spec file.",
    default="Trustlines",
)
@project_name_option(default="custom")
@base_dir_option(default="custom")
@host_base_dir_option
@expose_ports_option
def custom(
    host_base_dir,
    docker_compose_file,
    base_dir,
    project_name,
    bridge_config,
    netstats_url,
    chain_dir,
    expose_node_ports,
):
    """
    Setup with custom settings.

    Setup all the necessary services for the custom node setup.
    """

    if netstats_url == LAIKA:
        netstats_url = LAIKA_NETSTATS_SERVER_BASE_URL
    elif netstats_url == TLBC:
        netstats_url = TLBC_NETSTATS_SERVER_BASE_URL

    run(
        "custom home blockchain",
        foreign_chain_name="foreign chain",
        base_dir=base_dir,
        chain_dir=chain_dir,
        bridge_config_file=bridge_config,
        docker_compose_file=docker_compose_file,
        netstats_url=netstats_url,
        project_name=project_name,
        host_base_dir=host_base_dir,
        expose_node_ports=expose_node_ports,
    )


def run(
    setup_name,
    *,
    foreign_chain_name,
    bridge_config_file,
    docker_compose_file,
    base_dir,
    project_name,
    chain_dir,
    netstats_url=None,
    host_base_dir=None,
    expose_node_ports=False,
):
    click.echo(
        "\n".join(
            (
                fill(
                    f"This script will guide you through the setup of a {setup_name} node as well as a few "
                    "additional services. The services will run in the background as "
                    "docker containers and will be automatically restarted on failures and updated to new versions. "
                    "For more information about the setup please checkout the Readme: "
                ),
                "https://github.com/trustlines-protocol/blockchain",
                fill(
                    "It is safe to run this script multiple times. Already existing containers will be "
                    "restarted and no configuration will be overwritten. It is possible to enable "
                    "additional components that you have chosen not to configure in earlier runs."
                ),
                "",
            )
        )
    )
    validator_account.setup_interactively(base_dir=base_dir, chain_dir=chain_dir)
    # not in use because of https://github.com/openethereum/openethereum/issues/11246
    # validator_account.setup_author_address(setup_name=setup_name, base_dir=base_dir)
    monitor.setup_interactively(base_dir=base_dir)
    bridge.setup_interactively(
        base_dir=base_dir,
        bridge_config_file=bridge_config_file,
        foreign_chain_name=foreign_chain_name,
    )
    netstats.setup_interactively(base_dir=base_dir, netstats_url=netstats_url)
    docker.setup_interactivaly(
        base_dir=base_dir,
        docker_compose_file=docker_compose_file,
        expose_node_ports=expose_node_ports,
    )
    docker.update_and_start(
        base_dir=base_dir,
        host_base_dir=host_base_dir,
        project_name=project_name,
        start_foreign_node=should_foreign_node_be_started(
            base_dir=base_dir, bridge_config_file=bridge_config_file
        ),
    )


def should_foreign_node_be_started(*, base_dir, bridge_config_file):
    if not utils.is_bridge_prepared(base_dir=base_dir):
        return False
    else:
        return bridge.is_bridge_using_template_json_rpc_url(
            base_dir, bridge_config_file
        )


if __name__ == "__main__":
    main()
