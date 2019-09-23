import os
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
    default=os.getcwd(),
)
def main(host_base_dir):
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

    validator_account.setup_interactively()
    monitor.setup_interactively()
    bridge.setup_interactively()
    netstats.setup_interactively()
    docker.update_and_start(host_base_dir)


if __name__ == "__main__":
    main()
