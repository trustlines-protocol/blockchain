import click
from web3 import Web3, EthereumTesterProvider

from validator_set_deploy.core import (
    deploy_validator_set_contract,
    initialize_validator_set_contract,
    read_addresses_in_csv,
    validate_and_format_address,
    InvalidAddressException,
    get_validator_contract,
)

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

# we need test_provider and test_json_rpc for running the tests in test_cli
# they need to persist between multiple calls to runner.invoke and are
# therefore initialized on the module level.
test_provider = EthereumTesterProvider()
test_json_rpc = Web3(test_provider)


def validate_address(
    ctx, param, value
):  # TODO: potentially reformat this to deploy-tools?
    """This function must be at the top of click commands using it"""
    try:
        return validate_and_format_address(value)
    except InvalidAddressException as e:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        ) from e


validator_set_address_option = click.option(
    "--address",
    "validator_contract_address",
    help='The address of the validator set contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
    envvar="VALIDATOR_CONTRACT_ADDRESS",
)

validator_file_option = click.option(
    "--validators",
    "validators_file",
    help="Path to the csv file containing the addresses of the validators",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)


@click.group()
def main():
    pass


@main.command(
    short_help="Deploys the validator set and initializes with the validator addresses."
)
@keystore_option
@validator_file_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy(
    keystore: str,
    validators_file: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    validator_set_contract = deploy_validator_set_contract(
        web3=web3, transaction_options=transaction_options, private_key=private_key
    )
    validators = read_addresses_in_csv(validators_file)
    initialize_validator_set_contract(
        web3=web3,
        transaction_options=transaction_options,
        validator_set_contract=validator_set_contract,
        validators=validators,
        private_key=private_key,
    )

    click.echo("ValidatorSet address: " + validator_set_contract.address)


@main.command(
    short_help="Check that the current validators of the contract are matching the one in the given file."
)
@validator_set_address_option
@validator_file_option
@jsonrpc_option
def check_validators(validator_contract_address, validators_file, jsonrpc):

    web3 = connect_to_json_rpc(jsonrpc)
    validators = read_addresses_in_csv(validators_file)

    validator_contract = get_validator_contract(
        web3=web3, address=validator_contract_address
    )
    current_validators = validator_contract.functions.getValidators().call()

    if validators == current_validators:
        click.echo(
            f"The current validators of the contract are matching the validators in the file {validators_file}"
        )
    else:
        click.secho(
            f"The current validators of the contract are not matching the validators in the file {validators_file}",
            fg="red",
        )
