import click
from eth_keyfile import extract_key_from_keyfile
from web3 import Web3


def decrypt_private_key(keystore: click.Path(), password: str):
    return extract_key_from_keyfile(str(keystore), password.encode("utf-8"))


jsonrpc_option = click.option(
    "--jsonrpc",
    help="JsonRPC URL of the ethereum client",
    default="http://127.0.0.1:8545",
    show_default=True,
    metavar="URL",
)

keystore_option = click.option(
    "--keystore",
    help="Path to the encrypted keystore",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
)
gas_option = click.option(
    "--gas", help="Gas of the transaction to be sent", type=int, default=None
)
gas_price_option = click.option(
    "--gas-price",
    help="Gas price of the transaction to be sent",
    type=int,
    default=None,
)
nonce_option = click.option(
    "--nonce", help="Nonce of the transaction to be sent", type=int, default=None
)


@click.group()
def main(prog_name="auction-deploy"):
    pass


@main.command(short_help="Deploy validator auction contract")
@click.option(
    "--start-price",
    help="Start Price of the auction in Ether",
    type=int,
    show_default=True,
    default=10000,
)
@click.option(
    "--duration",
    help="Duration of the auction in days",
    type=int,
    show_default=True,
    default=14,
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@jsonrpc_option
def deploy(start_price, duration, keystore, jsonrpc, gas, gas_price, nonce):

    web3 = Web3(  # noqa: F841
        Web3.HTTPProvider(jsonrpc, request_kwargs={"timeout": 180})
    )
    private_key = None

    if keystore is not None:
        password = click.prompt(
            "Please enter the password to decrypt the keystore",
            type=str,
            hide_input=True,
        )
        # password = b'test_password'
        private_key = decrypt_private_key(keystore, password)

    click.echo(private_key)
