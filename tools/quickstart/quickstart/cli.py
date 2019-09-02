import click

from quickstart import bridge, docker, netstats, validator_account


@click.command()
def main():
    validator_account.setup_interactively()
    netstats.setup_interactively()
    bridge.setup_interactively()
    docker.update_and_start()


if __name__ == "__main__":
    main()
