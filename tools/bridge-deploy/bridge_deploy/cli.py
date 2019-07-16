import click

from deploy_tools.cli import (
    jsonrpc_option,
    keystore_option,
    gas_option,
    gas_price_option,
    nonce_option,
    auto_nonce_option,
    connect_to_json_rpc,
    retrieve_private_key,
    get_nonce,
)
from deploy_tools.deploy import build_transaction_options
from deploy_tools.files import validate_and_format_address, InvalidAddressException

from bridge_deploy.foreign import deploy_foreign_bridge_contract


def validate_address(ctx, param, value):
    """This function must be at the top of click commands using it"""
    try:
        return validate_and_format_address(value)
    except InvalidAddressException as e:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        ) from e


token_address_option = click.option(
    "--token-address",
    help=("The address of the TrustlinesNetworkToken contract ('0x' prefixed string)."),
    type=str,
    required=True,
    callback=validate_address,
)


@click.group()
def main():
    pass


@main.command(
    short_help="Deploys the token bridge on the foreign network and initializes all contracts."
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
@token_address_option
def deploy_foreign(
    keystore: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
    token_address,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    foreign_bridge_contract = deploy_foreign_bridge_contract(
        token_contract_address=token_address,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )

    click.echo(f"ForeignBridge address: {foreign_bridge_contract.address}")
    click.echo(f"  deployed at block #{web3.eth.blockNumber}")


@main.command(
    short_help="Print all information on the latest foreign bridge deployment."
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def print_foreign(
    keystore: str, jsonrpc: str, gas: int, gas_price: int, nonce: int, auto_nonce: bool
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    # transaction_options = build_transaction_options(
    #     gas=gas, gas_price=gas_price, nonce=nonce
    # )

    # TODO: Implement me
