import os

import click

from quickstart import bridge, docker, netstats, validator_account


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
    validator_account.setup_interactively()
    bridge.setup_interactively()
    netstats.setup_interactively()
    docker.update_and_start(host_base_dir)


if __name__ == "__main__":
    main()
