from pathlib import PosixPath
from enum import Enum

import click
from web3 import Web3, EthereumTesterProvider, Account
from deploy_tools.deploy import send_function_call_transaction
from eth_utils import is_address, to_checksum_address

from auction_deploy.core import (
    deploy_auction_contracts,
    initialize_auction_contracts,
    decrypt_private_key,
    build_transaction_options,
    AuctionOptions,
    get_deployed_auction_contracts,
)


def validate_address(ctx, param, value):
    """This function must be at the top of click commands using it"""
    if is_address(value):
        return to_checksum_address(value)
    else:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        )


test_json_rpc = Web3(EthereumTesterProvider())
ETH_IN_WEI = 10 ** 18


# This has to be in sync with the AuctionStates in ValidatorAuction.sol
class AuctionState(Enum):
    Deployed = 0
    Started = 1
    DepositPending = 2
    Ended = 3
    Failed = 4


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
    "--nonce", help="Nonce of the first transaction to be sent", type=int, default=None
)
auto_nonce_option = click.option(
    "--auto-nonce",
    help="automatically determine the nonce of first transaction to be sent",
    default=False,
    is_flag=True,
)


@click.group()
def main():
    pass


@main.command(
    short_help="Deploys validator auction, deposit locker, and slasher contract. "
    "Initializes the contracts."
)
@click.option(
    "--start-price",
    help="Start Price of the auction in Eth",
    type=int,
    show_default=True,
    default=10000,
)
@click.option(
    "--duration",
    "auction_duration",
    help="Duration of the auction in days",
    type=int,
    show_default=True,
    default=14,
)
@click.option(
    "--participants",
    "number_of_participants",
    help="Number of participants necessary to finish the auction successfully",
    type=int,
    show_default=True,
    default=123,
)
@click.option(
    "--release-block",
    "release_block_number",
    help="The release block number of the deposit locker",
    type=int,
    required=True,
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deploy(
    start_price: int,
    auction_duration: int,
    number_of_participants: int,
    release_block_number: int,
    keystore: PosixPath,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    auction_options = AuctionOptions(
        start_price * ETH_IN_WEI,
        auction_duration,
        number_of_participants,
        release_block_number,
    )

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )
    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    contracts = deploy_auction_contracts(
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
        auction_options=auction_options,
    )

    initialize_auction_contracts(
        web3=web3,
        transaction_options=transaction_options,
        contracts=contracts,
        release_block_number=release_block_number,
        private_key=private_key,
    )

    click.echo("Auction address: " + contracts.auction.address)
    click.echo("Deposit locker address: " + contracts.locker.address)
    click.echo("Validator slasher address: " + contracts.slasher.address)


@main.command(short_help="Start the auction at corresponding address.")
@click.option(
    "--auction-address",
    help='The address of the auction contract to be started, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def start_auction(
    auction_address,
    keystore: PosixPath,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
):

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)
    contracts = get_deployed_auction_contracts(web3, auction_address)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )

    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    auction_start = contracts.auction.functions.startAuction()

    send_function_call_transaction(
        auction_start,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


@main.command(
    short_help="Prints the values of variables necessary to monitor the auction."
)
@click.option(
    "--auction-address",
    help='The address of the auction contract to be checked, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
)
@jsonrpc_option
def print_auction_status(auction_address, jsonrpc):

    web3 = connect_to_json_rpc(jsonrpc)

    contracts = get_deployed_auction_contracts(web3, auction_address)

    # constants throughout auction
    duration_in_days = contracts.auction.functions.auctionDurationInDays().call()
    start_price_in_eth = contracts.auction.functions.startPrice().call() / ETH_IN_WEI
    number_of_participants = contracts.auction.functions.numberOfParticipants().call()
    locker_address = contracts.locker.address
    slasher_address = contracts.slasher.address
    locker_initialized = contracts.locker.functions.initialized().call()
    slasher_initialized = contracts.slasher.functions.initialized().call()

    # variables
    auction_state_value = contracts.auction.functions.auctionState().call()
    auction_state = AuctionState(auction_state_value)
    start_time = contracts.auction.functions.startTime().call()
    close_time = contracts.auction.functions.closeTime().call()
    closing_price = contracts.auction.functions.closingPrice().call()
    if auction_state == AuctionState.Started:
        current_price_in_eth = (
            contracts.auction.functions.currentPrice().call() / ETH_IN_WEI
        )

    click.echo(
        "The auction duration is:                " + str(duration_in_days) + " days"
    )
    click.echo(
        "The starting price in eth is:           " + str(start_price_in_eth) + " eth"
    )
    click.echo("The number of participants is:          " + str(number_of_participants))
    click.echo("The address of the locker contract is:  " + str(locker_address))
    click.echo("The address of the slasher contract is: " + str(slasher_address))
    click.echo("The locker initialized value is:        " + str(locker_initialized))
    click.echo("The slasher initialized value is:       " + str(slasher_initialized))

    click.echo(
        "------------------------------------    ------------------------------------------"
    )

    click.echo(
        "The auction state is:                   "
        + str(auction_state_value)
        + " ("
        + str(auction_state.name)
        + ")"
    )
    click.echo("The start time is:                      " + str(start_time))
    click.echo("The close time is:                      " + str(close_time))
    if auction_state == auction_state.Started:
        click.echo(
            "The current price is:                   "
            + str(current_price_in_eth)
            + " eth"
        )
    click.echo("The closing price is:                   " + str(closing_price))


def connect_to_json_rpc(jsonrpc) -> Web3:
    if jsonrpc == "test":
        web3 = test_json_rpc
    else:
        web3 = Web3(Web3.HTTPProvider(jsonrpc, request_kwargs={"timeout": 180}))
    return web3


def retrieve_private_key(keystore):
    """
    return the private key corresponding to keystore or none if keystore is none
    """

    private_key = None

    if keystore is not None:
        password = click.prompt(
            "Please enter the password to decrypt the keystore",
            type=str,
            hide_input=True,
        )
        private_key = decrypt_private_key(str(keystore), password)

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
