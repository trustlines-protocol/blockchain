import click
from web3 import Web3, EthereumTesterProvider

from validator_set_deploy.core import (
    deploy_validator_set_contract,
    initialize_validator_set_contract,
    get_validator_contract,
    deploy_validator_proxy_contract,
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
from deploy_tools.files import (
    read_addresses_in_csv,
    validate_and_format_address,
    InvalidAddressException,
)

# we need test_provider and test_json_rpc for running the tests in test_cli
# they need to persist between multiple calls to runner.invoke and are
# therefore initialized on the module level.
test_provider = EthereumTesterProvider()
test_json_rpc = Web3(test_provider)


def validate_address(
    ctx, param, value
):  # TODO: take this from deploy_tools once new version is available
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
@click.option(
    "--address",
    "validator_proxy_address",
    help='The address of the validator proxy contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
    envvar="VALIDATOR_PROXY_ADDRESS",
)
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy(
    keystore: str,
    validators_file: str,
    validator_proxy_address: str,
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
        validator_proxy_address=validator_proxy_address,
        private_key=private_key,
    )

    click.echo("ValidatorSet address: " + validator_set_contract.address)


@main.command(
    short_help="Deploys the validator proxy and initializes with the validator addresses "
    "within the given validator set address."
)
@keystore_option
@click.option(
    "--validators",
    "validators_file",
    help="Path to the csv file containing the addresses of the validators",
    type=click.Path(),
    required=False,
)
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy_proxy(
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

    validators: list = []
    if validators_file:
        validators = read_addresses_in_csv(validators_file)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    validator_proxy_contract = deploy_validator_proxy_contract(
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
        validators=validators,
    )

    click.echo("ValidatorProxy address: " + validator_proxy_contract.address)


@main.command(
    short_help="Check that the current validators of the contract are matching the one in the given file."
)
@validator_set_address_option
@validator_file_option
@jsonrpc_option
def check_validators(validator_contract_address, validators_file, jsonrpc):

    web3 = connect_to_json_rpc(jsonrpc)
    validators_from_file = read_addresses_in_csv(validators_file)

    validator_contract = get_validator_contract(
        web3=web3, address=validator_contract_address
    )
    current_validators = validator_contract.functions.getValidators().call()

    click.echo("The current validators are:")
    for validator in current_validators:
        if validator in validators_from_file:
            click.echo(validator)
        else:
            click.secho(f"+{validator}", fg="green")

    click.echo()
    click.echo("The missing validators in the contract are:")
    for validator in validators_from_file:
        if validator not in current_validators:
            click.secho(f"-{validator}", fg="red")

    click.echo()
    click.echo("Legend:")
    click.echo("0xaddress: both in contract and in file")
    click.secho("+0xaddress: in contract but not in csv file", fg="green")
    click.secho("-0xaddress: in csv file but not in contract", fg="red")
    click.echo()

    if validators_from_file == current_validators:
        click.echo(
            f"The current validators of the contract are matching the validators in the file {validators_file}"
        )
    else:
        click.secho(
            f"The current validators of the contract are not matching the validators in the file {validators_file}",
            fg="red",
        )


@main.command(short_help="Prints the current validators.")
@validator_set_address_option
@jsonrpc_option
def print_validators(validator_contract_address, jsonrpc):

    web3 = connect_to_json_rpc(jsonrpc)
    validator_contract = get_validator_contract(
        web3=web3, address=validator_contract_address
    )
    current_validators = validator_contract.functions.getValidators().call()

    click.echo("The current validators are:")
    click.echo()
    for validator in current_validators:
        click.echo(validator)
