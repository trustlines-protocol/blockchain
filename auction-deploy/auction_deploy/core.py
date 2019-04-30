import json
import pkg_resources
from typing import Dict, NamedTuple
from collections import namedtuple

from eth_keyfile import extract_key_from_keyfile
from deploy_tools.deploy import send_function_call_transaction, deploy_compiled_contract


class AuctionOptions(NamedTuple):
    start_price: int
    auction_duration: int
    number_of_participants: int
    release_block_number: int


DeployedAuctionContracts = namedtuple("DeployedContracts", "locker slasher auction")


def load_contracts_json() -> Dict:
    resource_package = __name__
    stream = pkg_resources.resource_stream(resource_package, "contracts.json")
    json_string = stream.read().decode()
    stream.close()
    return json.loads(json_string)


def decrypt_private_key(keystore: str, password: str) -> bytes:
    return extract_key_from_keyfile(keystore, password.encode("utf-8"))


def increase_transaction_options_nonce(transaction_options: Dict) -> None:
    if "nonce" in transaction_options:
        transaction_options["nonce"] = transaction_options["nonce"] + 1


def deploy_auction_contracts(
    *,
    web3,
    transaction_options: Dict = None,
    private_key=None,
    auction_options: AuctionOptions,
) -> DeployedAuctionContracts:

    if transaction_options is None:
        transaction_options = {}

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
        auction_options.start_price,
        auction_options.auction_duration,
        auction_options.number_of_participants,
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

    contracts = DeployedAuctionContracts(
        deposit_locker_contract, validator_slasher_contract, auction_contract
    )

    return contracts


def initialize_auction_contracts(
    *,
    web3,
    transaction_options=None,
    contracts: DeployedAuctionContracts,
    release_block_number,
    private_key=None,
) -> None:
    if transaction_options is None:
        transaction_options = {}

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