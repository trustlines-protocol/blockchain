from enum import Enum

import click
from web3 import Web3, EthereumTesterProvider, Account
from deploy_tools.deploy import send_function_call_transaction

from auction_deploy.core import (
    deploy_auction_contracts,
    initialize_auction_contracts,
    decrypt_private_key,
    build_transaction_options,
    AuctionOptions,
    get_deployed_auction_contracts,
    whitelist_addresses,
    read_whitelist,
    validate_and_format_address,
    InvalidAddressException,
    missing_whitelisted_addresses,
)

# we need test_provider and test_json_rpc for running the tests in test_cli
# they need to persist between multiple calls to runner.invoke and are
# therefore initialized on the module level.
test_provider = EthereumTesterProvider()
test_json_rpc = Web3(test_provider)

ETH_IN_WEI = 10 ** 18


def validate_address(ctx, param, value):
    """This function must be at the top of click commands using it"""
    try:
        return validate_and_format_address(value)
    except InvalidAddressException as e:
        raise click.BadParameter(
            f"The address parameter is not recognized to be an address: {value}"
        ) from e


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


auction_address_option = click.option(
    "--address",
    "auction_address",
    help='The address of the auction contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
)
whitelist_file_option = click.option(
    "--file",
    "whitelist_file",
    help="Path to the csv file containing the addresses to be whitelisted",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
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
    "--release-timestamp",
    "release_timestamp",
    help="The release timestamp of the deposit locker",
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
    release_timestamp: int,
    keystore: str,
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
        release_timestamp,
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
        release_timestamp=release_timestamp,
        private_key=private_key,
    )

    click.echo("Auction address: " + contracts.auction.address)
    click.echo("Deposit locker address: " + contracts.locker.address)
    click.echo("Validator slasher address: " + contracts.slasher.address)


@main.command(short_help="Start the auction at corresponding address.")
@auction_address_option
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def start(
    auction_address,
    keystore: str,
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
    short_help="Move the bids from the auction contract to the deposit locker."
)
@auction_address_option
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def deposit_bids(
    auction_address,
    keystore: str,
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

    deposit_bids_call = contracts.auction.functions.depositBids()

    send_function_call_transaction(
        deposit_bids_call,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


@main.command(short_help="Close the auction at corresponding address.")
@auction_address_option
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def close(
    auction_address,
    keystore: str,
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

    auction_close = contracts.auction.functions.closeAuction()

    send_function_call_transaction(
        auction_close,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )


@main.command(
    short_help="Prints the values of variables necessary to monitor the auction."
)
@auction_address_option
@jsonrpc_option
def status(auction_address, jsonrpc):

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


@main.command(short_help="Whitelists addresses for the auction")
@whitelist_file_option
@auction_address_option
@click.option(
    "--batch-size",
    help="Number of addresses to be whitelisted within one transaction",
    type=click.IntRange(min=1),
    show_default=True,
    default=100,
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
def whitelist(
    whitelist_file: str,
    auction_address: str,
    batch_size: int,
    keystore: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
) -> None:

    web3 = connect_to_json_rpc(jsonrpc)
    whitelist = read_whitelist(whitelist_file)
    private_key = retrieve_private_key(keystore)

    nonce = get_nonce(
        web3=web3, nonce=nonce, auto_nonce=auto_nonce, private_key=private_key
    )

    transaction_options = build_transaction_options(
        gas=gas, gas_price=gas_price, nonce=nonce
    )

    contracts = get_deployed_auction_contracts(web3, auction_address)

    number_of_whitelisted_addresses = whitelist_addresses(
        contracts.auction,
        whitelist,
        batch_size=batch_size,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    click.echo(
        "Number of whitelisted addresses: " + str(number_of_whitelisted_addresses)
    )


@main.command(
    short_help="Check number of not yet whitelisted addresses for the auction"
)
@whitelist_file_option
@auction_address_option
@jsonrpc_option
def check_whitelist(whitelist_file: str, auction_address: str, jsonrpc: str) -> None:
    web3 = connect_to_json_rpc(jsonrpc)
    whitelist = read_whitelist(whitelist_file)
    contracts = get_deployed_auction_contracts(web3, auction_address)

    number_of_missing_addresses = len(
        missing_whitelisted_addresses(contracts.auction, whitelist)
    )

    if number_of_missing_addresses == 0:
        click.echo(f"All {len(whitelist)} addresses have been whitelisted")
    else:
        click.echo(
            f"{number_of_missing_addresses} of {len(whitelist)} addresses have not been whitelisted yet"
        )


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
