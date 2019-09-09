import os

import click

from quickstart import bridge, docker, netstats, validator_account


@click.command()
@click.option(
    "--host-base-dir",
    help=(
        "absolute path to use for docker volumes "
        "(only relevant when run from inside a docker container itself)"
    ),
    default=os.getcwd(),
)
def main(host_base_dir):
    setup_as_validator = prompt_setup_as_validator()
    if setup_as_validator:
        validator_account.setup_interactively()
        bridge.setup_interactively()
    netstats.setup_interactively()
    docker.update_and_start(host_base_dir, as_validator=setup_as_validator)


def prompt_setup_as_validator():
    choice = click.prompt(
        "Do you want to setup a validator (1) a regular node (2)?",
        type=click.Choice(("1", "2")),
        show_choices=False,
    )
    if choice == "1":
        return True
    elif choice == "2":
        return False
    else:
        assert False, "unreachable"


if __name__ == "__main__":
    main()
