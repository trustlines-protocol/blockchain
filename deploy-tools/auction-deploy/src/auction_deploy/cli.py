from enum import Enum
from os import linesep
from typing import Optional

import click
import pendulum
from deploy_tools.cli import (
    auto_nonce_option,
    connect_to_json_rpc,
    gas_option,
    gas_price_option,
    get_nonce,
    jsonrpc_option,
    keystore_option,
    nonce_option,
    retrieve_private_key,
    validate_address,
)
from deploy_tools.deploy import (
    build_transaction_options,
    send_function_call_transaction,
)
from deploy_tools.files import read_addresses_in_csv
from web3.contract import Contract

from auction_deploy.core import (
    ZERO_ADDRESS,
    AuctionOptions,
    DeployedAuctionContracts,
    DeployedContractsAddresses,
    deploy_auction_contracts,
    get_bid_token_address,
    get_deployed_auction_contracts,
    initialize_auction_contracts,
    missing_whitelisted_addresses,
    whitelist_addresses,
)

ETH_IN_WEI = 10 ** 18


def validate_date(ctx, param, value):
    if value is None:
        return None
    try:
        return pendulum.parse(value)
    except pendulum.parsing.exceptions.ParserError as e:
        raise click.BadParameter(
            f'The parameter "{value}" cannot be parsed as a date. (Try e.g. "2020-09-28", "2020-09-28T13:56")'
        ) from e


def validate_optional_address(ctx, param, value):
    if value is None:
        return value
    else:
        return validate_address(ctx, param, value)


# This has to be in sync with the AuctionStates in BaseValidatorAuction.sol
class AuctionState(Enum):
    Deployed = 0
    Started = 1
    DepositPending = 2
    Ended = 3
    Failed = 4


auction_address_option = click.option(
    "--address",
    "auction_address",
    help='The address of the auction contract, "0x" prefixed string',
    type=str,
    required=True,
    callback=validate_address,
    metavar="ADDRESS",
    envvar="AUCTION_DEPLOY_ADDRESS",
)
whitelist_file_option = click.option(
    "--file",
    "whitelist_file",
    help="Path to the csv file containing the addresses to be whitelisted",
    type=click.Path(exists=True, dir_okay=False),
    required=True,
)
already_deployed_auction_option = click.option(
    "--auction",
    "already_deployed_auction",
    help="Address of an already deployed auction contract to resume deployment with.",
    type=str,
    callback=validate_optional_address,
    required=False,
)
already_deployed_locker_option = click.option(
    "--locker",
    "already_deployed_locker",
    help="Address of an already deployed / init deposit locker to resume deployment with.",
    type=str,
    callback=validate_optional_address,
    required=False,
)
already_deployed_slasher_option = click.option(
    "--slasher",
    "already_deployed_slasher",
    help="Address of an already deployed / init validator slasher to resume deployment with.",
    type=str,
    callback=validate_optional_address,
    required=False,
)


def get_errors_messages_on_contracts_links(all_contracts: DeployedAuctionContracts):

    locker_address = all_contracts.locker.address

    locker_address_in_auction_contract = (
        all_contracts.auction.functions.depositLocker().call()
    )
    auction_address_in_locker_contract = (
        all_contracts.locker.functions.depositorsProxy().call()
    )
    slasher_address_in_locker_contract = all_contracts.locker.functions.slasher().call()

    locker_address_in_slasher_contract = ZERO_ADDRESS
    if all_contracts.slasher is not None:
        locker_address_in_slasher_contract = (
            all_contracts.slasher.functions.depositContract().call()
        )

    slasher_address = ZERO_ADDRESS
    if all_contracts.slasher is not None:
        slasher_address = all_contracts.slasher.address

    warning_messages = []
    if locker_address_in_auction_contract != locker_address:
        warning_messages.append(
            "The locker address in the auction contract does not match to the locker address."
        )
    if auction_address_in_locker_contract != all_contracts.auction.address:
        warning_messages.append(
            "The auction address in the locker contract does not match the auction address."
        )
    if slasher_address_in_locker_contract != slasher_address:
        warning_messages.append(
            "The slasher address in the locker contract does not match the slasher address."
        )
    if locker_address_in_slasher_contract != locker_address:
        warning_messages.append(
            "The locker address in the slasher contract does not match the locker address."
        )

    return warning_messages


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
    "--min-participants",
    "minimal_number_of_participants",
    help="Number of participants necessary to be able to close the auction successfully",
    type=int,
    show_default=True,
    default=50,
)
@click.option(
    "--max-participants",
    "maximal_number_of_participants",
    help="Maximal number of participants for the auction",
    type=int,
    show_default=True,
    default=123,
)
@click.option(
    "--use-token",
    is_flag=True,
    help="Whether to deploy a token validator auction or a regular eth auction",
)
@click.option(
    "--token-address",
    "token_address",
    help="The address of the token used for bidding in the case of a token validator auction",
    type=str,
    required=False,
)
@click.option(
    "--release-timestamp",
    "release_timestamp",
    help="The release timestamp of the deposit locker",
    type=int,
    required=False,
)
@click.option(
    "--release-date",
    "release_date",
    help='The release date of the deposit locker (e.g. "2020-09-28", "2020-09-28T13:56")',
    type=str,
    required=False,
    metavar="DATE",
    callback=validate_date,
)
@keystore_option
@gas_option
@gas_price_option
@nonce_option
@auto_nonce_option
@jsonrpc_option
@already_deployed_auction_option
@already_deployed_locker_option
@already_deployed_slasher_option
def deploy(
    start_price: int,
    auction_duration: int,
    minimal_number_of_participants: int,
    maximal_number_of_participants: int,
    use_token: bool,
    token_address: Optional[str],
    release_timestamp: int,
    release_date: pendulum.DateTime,
    keystore: str,
    jsonrpc: str,
    gas: int,
    gas_price: int,
    nonce: int,
    auto_nonce: bool,
    already_deployed_auction,
    already_deployed_locker,
    already_deployed_slasher,
) -> None:

    if use_token and token_address is None:
        raise click.BadParameter(
            "The flag `use-token` was provided, the token address must also be provided via `token-address`"
        )
    if token_address is not None and not use_token:
        raise click.BadParameter(
            "A token address has been provided, "
            "please use the flag --use-token to confirm you want to deploy a token auction"
        )

    if release_date is not None and release_timestamp is not None:
        raise click.BadParameter(
            "Both --release-date and --release-timestamp have been specified"
        )
    if release_date is None and release_timestamp is None:
        raise click.BadParameter(
            "Please specify a release date with --release-date or --release-timestamp"
        )

    if already_deployed_auction is not None and already_deployed_locker is None:
        raise click.BadOptionUsage(
            "--auction",
            "Cannot resume deployment from already deployed auction without already deployed locker. "
            "Locker address is part of auction's constructor argument.",
        )

    if release_date is not None:
        release_timestamp = int(release_date.timestamp())

    web3 = connect_to_json_rpc(jsonrpc)
    private_key = retrieve_private_key(keystore)

    auction_options = AuctionOptions(
        start_price * ETH_IN_WEI,
        auction_duration,
        minimal_number_of_participants,
        maximal_number_of_participants,
        release_timestamp,
        token_address,
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
        already_deployed_contracts=DeployedContractsAddresses(
            already_deployed_locker, already_deployed_slasher, already_deployed_auction
        ),
    )

    initialize_auction_contracts(
        web3=web3,
        transaction_options=transaction_options,
        contracts=contracts,
        release_timestamp=release_timestamp,
        token_address=token_address,
        private_key=private_key,
    )
    slasher: Contract = contracts.slasher

    click.echo("Auction address: " + contracts.auction.address)
    click.echo("Deposit locker address: " + contracts.locker.address)
    click.echo("Validator slasher address: " + slasher.address)
    warning_messages = get_errors_messages_on_contracts_links(contracts)
    if warning_messages:
        warning_messages.append("Verify what is wrong with `auction-deploy status`.")
        click.secho(linesep.join(warning_messages), fg="red")


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


def format_timestamp(timestamp: int):
    if timestamp:
        date_string = pendulum.from_timestamp(timestamp).to_iso8601_string()
        return f"{timestamp} ({date_string})"
    else:
        return f"{timestamp}"


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
    start_price_in_biggest_unit = (
        contracts.auction.functions.startPrice().call() / ETH_IN_WEI
    )
    minimal_number_of_participants = (
        contracts.auction.functions.minimalNumberOfParticipants().call()
    )
    maximal_number_of_participants = (
        contracts.auction.functions.maximalNumberOfParticipants().call()
    )
    bid_token_address = get_bid_token_address(web3, auction_address)
    locker_address = contracts.locker.address
    locker_initialized = contracts.locker.functions.initialized().call()
    locker_release_timestamp = contracts.locker.functions.releaseTimestamp().call()

    slasher_address = ZERO_ADDRESS
    slasher_initialized = False
    if contracts.slasher is not None:
        slasher_address = contracts.slasher.address
        slasher_initialized = contracts.slasher.functions.initialized().call()

    # variables
    auction_state_value = contracts.auction.functions.auctionState().call()
    auction_state = AuctionState(auction_state_value)
    start_time = contracts.auction.functions.startTime().call()
    close_time = contracts.auction.functions.closeTime().call()
    last_slot_price = contracts.auction.functions.lowestSlotPrice().call()
    current_price_in_eth = 0
    if auction_state == AuctionState.Started:
        current_price_in_eth = (
            contracts.auction.functions.currentPrice().call() / ETH_IN_WEI
        )

    click.echo(
        "The auction duration is:                " + str(duration_in_days) + " days"
    )
    click.echo(
        "The starting price is:                  "
        + str(start_price_in_biggest_unit)
        + " ETH/TLN"
    )
    click.echo(
        "The minimal number of participants is:  " + str(minimal_number_of_participants)
    )
    click.echo(
        "The maximal number of participants is:  " + str(maximal_number_of_participants)
    )
    if bid_token_address is not None:
        click.echo("The address of the bid token is:        " + str(bid_token_address))
    click.echo("The address of the locker contract is:  " + str(locker_address))
    click.echo("The locker initialized value is:        " + str(locker_initialized))
    if contracts.slasher is not None:
        click.echo("The address of the slasher contract is: " + str(slasher_address))
        click.echo(
            "The slasher initialized value is:       " + str(slasher_initialized)
        )
    else:
        click.secho("The slasher contract cannot be found.", fg="red")

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
    click.echo(
        "The start time is:                      " + format_timestamp(start_time)
    )
    click.echo(
        "The close time is:                      " + format_timestamp(close_time)
    )
    if auction_state == auction_state.Started:
        click.echo(
            "The current price is:                   "
            + str(current_price_in_eth)
            + " ETH/TLN"
        )
    click.echo("The last slot price is:                 " + str(last_slot_price))
    click.echo(
        "Deposits will be locked until:          "
        + format_timestamp(locker_release_timestamp)
    )

    click.echo(
        "------------------------------------    ------------------------------------------"
    )

    warning_messages = get_errors_messages_on_contracts_links(contracts)
    if warning_messages:
        click.secho(linesep.join(warning_messages), fg="red")


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
    whitelist = read_addresses_in_csv(whitelist_file)
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
    whitelist = read_addresses_in_csv(whitelist_file)
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
