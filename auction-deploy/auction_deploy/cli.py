from collections import namedtuple

import click
from eth_keyfile import extract_key_from_keyfile
from web3 import Web3, EthereumTesterProvider
from deploy_tools.deploy import send_function_call_transaction, deploy_compiled_contract

from .core import load_contracts_json


ContractOptions = namedtuple(
    "ContractOptions",
    "start_price auction_duration number_of_participants release_block_number",
)  # TODO change to validator options
DeployedContracts = namedtuple("DeployedContracts", "locker slasher auction")


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
def main(prog_name="auction-deploy"):
    pass


@main.command(
    short_help="Deploys validator auction, deposit locker, and slasher contract. "
    "Initializes the contracts."
)
@click.option(
    "--start-price",
    help="Start Price of the auction in wei",
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
    help="Duration of the auction in days",
    type=int,
    show_default=True,
    default=14,
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
    start_price,
    auction_duration,
    number_of_participants,
    release_block_number,
    keystore,
    jsonrpc,
    gas,
    gas_price,
    nonce,
):

    if jsonrpc == "test":
        web3 = Web3(EthereumTesterProvider())
    else:
        web3 = Web3(Web3.HTTPProvider(jsonrpc, request_kwargs={"timeout": 180}))
    private_key = None

    if keystore is not None:
        password = click.prompt(
            "Please enter the password to decrypt the keystore",
            type=str,
            hide_input=True,
        )
        private_key = decrypt_private_key(keystore, password)

    contract_options = ContractOptions(
        start_price, auction_duration, number_of_participants, release_block_number
    )

    transaction_options = {}

    if gas is not None:
        transaction_options["gas"] = gas
    if gas is not None:
        transaction_options["gasPrice"] = gas_price
    if gas is not None:
        transaction_options["nonce"] = nonce

    contracts = deploy_contracts(
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
        contract_options=contract_options,
    )

    initialize_contracts(
        web3=web3,
        transaction_options=transaction_options,
        contracts=contracts,
        release_block_number=release_block_number,
        private_key=private_key,
    )

    click.echo("Auction address: " + contracts.auction.address)
    click.echo("Deposit locker address: " + contracts.locker.address)
    click.echo("Validator slasher address: " + contracts.slasher.address)


def decrypt_private_key(keystore: click.Path(), password: str):
    return extract_key_from_keyfile(str(keystore), password.encode("utf-8"))


def increase_transaction_options_nonce(transaction_options):
    if "nonce" in transaction_options:
        transaction_options["nonce"] = transaction_options["nonce"] + 1


def deploy_contracts(
    *, web3, transaction_options={}, private_key=None, contract_options: ContractOptions
) -> DeployedContracts:

    compiled_contracts = load_contracts_json()

    deposit_locker_abi = compiled_contracts["DepositLocker"]["abi"]
    deposit_locker_bin = compiled_contracts["DepositLocker"]["bytecode"]

    validator_slasher_abi = compiled_contracts["ValidatorSlasher"]["abi"]
    validator_slasher_bin = compiled_contracts["ValidatorSlasher"]["bytecode"]

    auction_abi = compiled_contracts["ValidatorAuction"]["abi"]
    auction_bin = compiled_contracts["ValidatorAuction"]["bytecode"]

    deposit_locker_contract = deploy_compiled_contract(
        abi=deposit_locker_abi,
        bytecode=deposit_locker_bin,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )

    increase_transaction_options_nonce(transaction_options)

    validator_slasher_contract = deploy_compiled_contract(
        abi=validator_slasher_abi,
        bytecode=validator_slasher_bin,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    auction_constructor_args = (
        contract_options.start_price,
        contract_options.auction_duration,
        contract_options.number_of_participants,
        validator_slasher_contract.address,
    )

    auction_contract = deploy_compiled_contract(
        abi=auction_abi,
        bytecode=auction_bin,
        web3=web3,
        constructor_args=auction_constructor_args,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    contracts = DeployedContracts(
        deposit_locker_contract, validator_slasher_contract, auction_contract
    )

    return contracts


def initialize_contracts(
    *,
    web3,
    transaction_options={},
    contracts: DeployedContracts,
    release_block_number,
    private_key=None,
):

    deposit_init = contracts.locker.functions.init(
        release_block_number, contracts.slasher.address, contracts.auction.address
    )
    send_function_call_transaction(
        deposit_init,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)

    slasher_init = contracts.slasher.functions.init(contracts.locker.address)
    send_function_call_transaction(
        slasher_init,
        web3=web3,
        transaction_options=transaction_options,
        private_key=private_key,
    )
    increase_transaction_options_nonce(transaction_options)
