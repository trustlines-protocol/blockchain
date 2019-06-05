import click

# from web3 import Web3, EthereumTesterProvider

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

from bridge_deploy.core import validate_and_format_address, InvalidAddressException
from bridge_deploy.deploy_home import (
    deploy_bridge_home_contract,
    initialize_bridge_home_contract,
)

# we need test_provider and test_json_rpc for running the tests in test_cli
# they need to persist between multiple calls to runner.invoke and are
# therefore initialized on the module level.
# --- Is this even necessary? The test_rpc is already defined in deploy tools
# test_provider = EthereumTesterProvider()
# test_json_rpc = Web3(test_provider)


def validate_address(
    ctx, param, value
):  # TODO: potentially reformat this to deploy-tools? - Copypasta from validator-set-deploy. Refactoring might be a thing.
    """This function must be at the top of click commands using it"""
    try:
        return validate_and_format_address(value)
    except InvalidAddressException as e:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        ) from e


validator_contract_address_option = click.option(
    "--address",
    "validator_contract_address",
    help='The address of the validator set contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
    envvar="VALIDATOR_CONTRACT_ADDRESS",
)


@click.group()
def main():
    pass


@main.command(
    short_help="Deploys the token bridge on the home network and initializes all contracts."
)
@keystore_option
@validator_contract_address_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy_home(
    keystore: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
    validator_contract_address,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    dir(transaction_options)

    deployment_result = deploy_bridge_home_contract(
        web3=web3, transaction_options=transaction_options, private_key=private_key
    )

    click.echo(f"HomeBridge address: {deployment_result.home_bridge.address}")
    click.echo(f"  deployed at block #{deployment_result.home_bridge_block_number}")

    init_result = initialize_bridge_home_contract(
        web3=web3,
        transaction_options=transaction_options,
        home_bridge_contract=deployment_result.home_bridge,
        private_key=private_key,
        validator_contract_address=validator_contract_address,
    )


@main.command(
    short_help="Deploys the token bridge on the foreign network and initializes all contracts."
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy_foreign(
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

    dir(transaction_options)

    # TODO: Implement me


@main.command(short_help="Print all information on the latest home bridge deployment.")
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def print_home(
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

    dir(transaction_options)

    # TODO: Implement me - We should be able to get all required information from the bridge contract
    #  See validator-set-deploy for address validation


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
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    dir(transaction_options)
