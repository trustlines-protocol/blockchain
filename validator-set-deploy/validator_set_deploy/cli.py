import click
from web3 import Web3, EthereumTesterProvider, Account

from validator_set_deploy.core import decrypt_private_key, build_transaction_options

# we need test_provider and test_json_rpc for running the tests in test_cli
# they need to persist between multiple calls to runner.invoke and are
# therefore initialized on the module level.
test_provider = EthereumTesterProvider()
test_json_rpc = Web3(test_provider)

ETH_IN_WEI = 10 ** 18

jsonrpc_option = click.option(
    "--jsonrpc",
    help="JsonRPC URL of the ethereum client",
    default="http://127.0.0.1:8545",
    show_default=True,
    metavar="URL",
    envvar="VALIDATOR_SET_DEPLOY_JSONRPC",
)
keystore_option = click.option(
    "--keystore",
    help="Path to the encrypted keystore",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    envvar="VALIDATOR_SET_DEPLOY_KEYSTORE",
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
    "--nonce", help="Nonce of the first transaction to be sent", type=int, default=None
)
auto_nonce_option = click.option(
    "--auto-nonce",
    help="automatically determine the nonce of first transaction to be sent",
    default=False,
    is_flag=True,
    envvar="VALIDATOR_SET_DEPLOY_AUTO_NONCE",
)


@click.group()
def main():
    pass


@main.command(
    short_help="Deploys the validator set and initializes with the validator addresses."
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy(
    keystore: str, jsonrpc: str, gas: int, gas_price: int, nonce: int, auto_nonce: bool
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    click.echo(transaction_options)


def connect_to_json_rpc(jsonrpc) -> Web3:
    if jsonrpc == "test":
        web3 = test_json_rpc
    else:
        web3 = Web3(Web3.HTTPProvider(jsonrpc, request_kwargs={"timeout": 180}))
    return web3


def retrieve_private_key(keystore_path):
    """
    return the private key corresponding to keystore or none if keystore is none
    """

    private_key = None

    if keystore_path is not None:
        password = click.prompt(
            "Please enter the password to decrypt the keystore",
            type=str,
            hide_input=True,
        )
        private_key = decrypt_private_key(keystore_path, password)

    return private_key


def get_nonce(*, web3: Web3, nonce: int, auto_nonce: bool, private_key: bytes):
    """get the nonce to be used as specified via command line options

     we do some option checking in this function. It would be better to do this
     before doing any real work, but we would need another function then.
    """
    if auto_nonce and not private_key:
        raise click.UsageError("--auto-nonce requires --keystore argument")
    if nonce is not None and auto_nonce:
        raise click.UsageError(
            "--nonce and --auto-nonce cannot be used at the same time"
        )

    if auto_nonce:
        return web3.eth.getTransactionCount(
            Account.privateKeyToAccount(private_key).address, block_identifier="pending"
        )
    else:
        return nonce
