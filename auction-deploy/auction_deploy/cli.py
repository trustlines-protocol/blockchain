from pathlib import PosixPath

import click
from auction_deploy.core import (
    deploy_auction_contracts,
    initialize_auction_contracts,
    decrypt_private_key,
    AuctionOptions,
    load_contracts_json,
)
from web3 import Web3, EthereumTesterProvider

test_json_rpc = Web3(EthereumTesterProvider())

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
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
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
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)

    private_key = None

    if keystore is not None:
        password = click.prompt(
            "Please enter the password to decrypt the keystore",
            type=str,
            hide_input=True,
        )
        private_key = decrypt_private_key(str(keystore), password)

    auction_options = AuctionOptions(
        start_price * 10 ** 18,
        auction_duration,
        number_of_participants,
        release_block_number,
    )

    transaction_options = {}

    if gas is not None:
        transaction_options["gas"] = gas
    if gas_price is not None:
        transaction_options["gasPrice"] = gas_price
    if nonce is not None:
        transaction_options["nonce"] = nonce

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


@main.command(
    short_help="Deploys validator auction, deposit locker, and slasher contract. "
    "Initializes the contracts."
)
@click.option(
    "--auction-address",
    help='The address of the auction contract to be checked, "0x" prefixed string',
    type=str,
)
@jsonrpc_option
def print_auction_status(auction_address, jsonrpc):
    web3 = connect_to_json_rpc(jsonrpc)

    auction_abi = load_contracts_json()["ValidatorAuction"]["abi"]

    auction = web3.eth.contract(address=auction_address, abi=auction_abi)

    eth_in_wei = 1_000_000_000_000_000_000

    # constants
    duration_in_days = auction.functions.auctionDurationInDays().call()
    start_price_in_eth = auction.functions.startPrice().call() / eth_in_wei
    number_of_participants = auction.functions.numberOfParticipants().call()
    locker_address = auction.functions.depositLocker().call()

    # variables
    auction_state = auction.functions.auctionState().call()
    start_time = auction.functions.startTime().call()
    close_time = auction.functions.closeTime().call()
    closing_price = auction.functions.closingPrice().call()
    current_price = auction.functions.currentPrice().call()

    # TODO: get status of initialized for both locker and slasher

    click.echo(
        "The auction duration is:                " + str(duration_in_days) + " days"
    )
    click.echo(
        "The starting price in eth is:           " + str(start_price_in_eth) + " eth"
    )
    click.echo("The number of participants is:          " + str(number_of_participants))
    click.echo("The address of the locker contract is:  " + str(locker_address))

    click.echo(
        "------------------------------------    ------------------------------------------"
    )

    click.echo("The auction state is:                   " + str(auction_state))
    click.echo("The start time is:                      " + str(start_time))
    click.echo("The close time is:                      " + str(close_time))
    click.echo("The current price is:                   " + str(current_price))
    click.echo("The closing price is:                   " + str(closing_price))


def connect_to_json_rpc(jsonrpc) -> Web3:
    if jsonrpc == "test":
        web3 = test_json_rpc
    else:
        web3 = Web3(Web3.HTTPProvider(jsonrpc, request_kwargs={"timeout": 180}))
    return web3
