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

from bridge_deploy.home import (
    deploy_home_block_reward_contract,
    deploy_home_bridge_validators_contract,
    deploy_home_bridge_contract,
    initialize_home_bridge_contract,
)

from bridge_deploy.foreign import deploy_foreign_bridge_contract

from decimal import Decimal, InvalidOperation

WEI_PER_ETH = 10 ** 18


def validate_address(ctx, param, value):
    """This function must be at the top of click commands using it"""
    try:
        return validate_and_format_address(value)
    except InvalidAddressException as e:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        ) from e


def validate_eth_amount(ctx, param, value):
    try:
        eth_decimal = Decimal(value)
    except InvalidOperation:
        raise click.BadParameter(f"{value} is not a valid decimal number")
    else:
        wei_amount = eth_decimal * WEI_PER_ETH

    if int(wei_amount) != wei_amount:
        raise click.BadParameter(f"{value} contains fractional Wei component")

    return int(wei_amount)


validator_set_address_option = click.option(
    "--validator-set-address",
    help=(
        "The address of the bridge validator set contract or proxy contract"
        ' that implements IBridgeValidators, "0x" prefixed string'
    ),
    type=str,
    required=True,
    callback=validate_address,
    metavar="VALIDATOR_SET_ADDRESS",
    envvar="VALIDATOR_SET_ADDRESS",
)

block_reward_address_option = click.option(
    "--block-reward-address",
    help='The address of the block reward contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="BLOCK_REWARD_ADDRESS",
    envvar="BLOCK_REWARD_ADDRESS",
)

home_daily_limit_option = click.option(
    "--home-daily-limit",
    help="The daily transfer limit for the home bridge in ETH",
    type=str,
    default="10000",
    callback=validate_eth_amount,
)

home_max_per_tx_option = click.option(
    "--home-max-per-tx",
    help="The maximum transfer limit for one transaction in ETH",
    type=str,
    default="5000",
    callback=validate_eth_amount,
)

home_min_per_tx_option = click.option(
    "--home-min-per-tx",
    help="The minimum transfer limit for one transaction in ETH",
    type=str,
    default="0.005",
    callback=validate_eth_amount,
)

home_gas_price_option = click.option(
    "--home-gas_price",
    help="The initial gas price on the home network in WEI",
    type=int,
    default=1_000_000_000,
)

required_block_confirmations_option = click.option(
    "--required-block-confirmations",
    help="The number of blocks to wait for finality",
    type=int,
    default=4,
)

owner_address_option = click.option(
    "--owner-address",
    help="The address of the (temporary) bridge owner. This is normally derrived from the private key.",
    type=str,
    required=True,
    callback=validate_address,
)

validator_proxy_address_option = click.option(
    "--validator-proxy-address",
    help=(
        "The address of the bridge validator set contract or proxy contract"
        ' that implements IBridgeValidators, "0x" prefixed string'
    ),
    type=str,
    required=True,
    callback=validate_address,
)

required_signatures_divisor_option = click.option(
    "--required-signatures-divisor",
    help="The number to divide the total amount of validators by",
    type=int,
    default=2,
)

required_signatures_multiplier_option = click.option(
    "--required-signatures-multiplier",
    help="The number to multiply the total amount of validators with",
    type=int,
    default=1,
)


@click.group()
def main():
    pass


@main.command(short_help="Deploys the block reward contract on the home network.")
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy_reward(
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

    reward_contract = deploy_home_block_reward_contract(
        web3=web3, transaction_options=transaction_options, private_key=private_key
    )

    click.echo(f"BlockRewardContract address: {reward_contract.address}")


@main.command(short_help="Deploys the bridge validators proxy on the home network.")
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@validator_proxy_address_option
@required_signatures_divisor_option
@required_signatures_multiplier_option
@jsonrpc_option
def deploy_validators(
    keystore: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
    validator_proxy_address,
    required_signatures_divisor,
    required_signatures_multiplier,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    bridge_validators_contract = deploy_home_bridge_validators_contract(
        web3=web3,
        transaction_options=transaction_options,
        validator_proxy=validator_proxy_address,
        required_signatures_divisor=required_signatures_divisor,
        required_signatures_multiplier=required_signatures_multiplier,
        private_key=private_key,
    )

    click.echo(
        f"BridgeValidatorsContract address: {bridge_validators_contract.address}"
    )


@main.command(
    short_help="Deploys the token bridge on the home network and initializes all contracts."
)
@keystore_option
@validator_set_address_option
@home_daily_limit_option
@home_max_per_tx_option
@home_min_per_tx_option
@home_gas_price_option
@required_block_confirmations_option
@block_reward_address_option
@owner_address_option
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
    validator_set_address,
    home_daily_limit,
    home_max_per_tx,
    home_min_per_tx,
    home_gas_price,
    required_block_confirmations,
    block_reward_address,
    owner_address,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    deployment_result = deploy_home_bridge_contract(
        web3=web3, transaction_options=transaction_options, private_key=private_key
    )

    click.echo(f"HomeBridge address: {deployment_result.home_bridge.address}")
    click.echo(f"  deployed at block #{deployment_result.home_bridge_block_number}")

    initialize_home_bridge_contract(
        web3=web3,
        transaction_options=transaction_options,
        home_bridge_contract=deployment_result.home_bridge,
        home_bridge_proxy_contract=deployment_result.home_bridge_proxy,
        validator_contract_address=validator_set_address,
        home_daily_limit=home_daily_limit,
        home_max_per_tx=home_max_per_tx,
        home_min_per_tx=home_min_per_tx,
        home_gas_price=home_gas_price,
        required_block_confirmations=required_block_confirmations,
        block_reward_address=block_reward_address,
        owner_address=owner_address,
        private_key=private_key,
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

    deployment_result = deploy_foreign_bridge_contract(
        web3=web3, transaction_options=transaction_options, private_key=private_key
    )

    click.echo(f"ForeignBridge address: {deployment_result.foreign_bridge.address}")
    click.echo(f"  deployed at block #{deployment_result.foreign_bridge_block_number}")


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
    # transaction_options = build_transaction_options(
    #     gas=gas, gas_price=gas_price, nonce=nonce
    # )

    # TODO: Implement me - We should be able to get all required information from the bridge contract


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
