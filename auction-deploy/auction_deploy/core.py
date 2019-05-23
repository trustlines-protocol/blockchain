import json
import csv
import pkg_resources
from typing import Dict, NamedTuple, Sequence

from web3.contract import Contract
from eth_keyfile import extract_key_from_keyfile
from eth_utils import is_address, to_checksum_address
from deploy_tools.deploy import send_function_call_transaction, deploy_compiled_contract


ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class AuctionOptions(NamedTuple):
    start_price: int
    auction_duration: int
    minimal_number_of_participants: int
    maximal_number_of_participants: int
    release_timestamp: int


class DeployedAuctionContracts(NamedTuple):
    locker: Contract
    slasher: Contract
    auction: Contract


def load_contracts_json() -> Dict:
    resource_package = __name__
    json_string = pkg_resources.resource_string(resource_package, "contracts.json")
    return json.loads(json_string)


def decrypt_private_key(keystore_path: str, password: str) -> bytes:
    return extract_key_from_keyfile(keystore_path, password.encode("utf-8"))


def build_transaction_options(*, gas, gas_price, nonce):

    transaction_options = {}

    if gas is not None:
        transaction_options["gas"] = gas
    if gas_price is not None:
        transaction_options["gasPrice"] = gas_price
    if nonce is not None:
        transaction_options["nonce"] = nonce

    return transaction_options


def increase_transaction_options_nonce(transaction_options: Dict) -> None:
    """Increases the nonce inside of `transaction_options` by 1 if present.
    If there is no nonce in `transaction_options`, this function will not do anything
    """
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

    deposit_locker_contract: Contract = deploy_compiled_contract(
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
        auction_options.minimal_number_of_participants,
        auction_options.maximal_number_of_participants,
        deposit_locker_contract.address,
    )
    auction_contract: Contract = deploy_compiled_contract(
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
    release_timestamp,
    private_key=None,
) -> None:
    if transaction_options is None:
        transaction_options = {}

    deposit_init = contracts.locker.functions.init(
        release_timestamp, contracts.slasher.address, contracts.auction.address
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


def get_deployed_auction_contracts(
    web3, auction_address: str
) -> DeployedAuctionContracts:

    compiled_contracts = load_contracts_json()

    auction_abi = compiled_contracts["ValidatorAuction"]["abi"]
    locker_abi = compiled_contracts["DepositLocker"]["abi"]
    slasher_abi = compiled_contracts["ValidatorSlasher"]["abi"]

    auction = web3.eth.contract(address=auction_address, abi=auction_abi)

    locker_address = auction.functions.depositLocker().call()
    locker = web3.eth.contract(address=locker_address, abi=locker_abi)

    slasher_address = locker.functions.slasher().call()
    if slasher_address == ZERO_ADDRESS:
        slasher = None
    else:
        slasher = web3.eth.contract(address=slasher_address, abi=slasher_abi)

    deployed_auction_contracts: DeployedAuctionContracts = DeployedAuctionContracts(
        locker, slasher, auction
    )

    return deployed_auction_contracts


def whitelist_addresses(
    auction_contract: Contract,
    whitelist: Sequence[str],
    *,
    batch_size,
    web3,
    transaction_options=None,
    private_key=None,
) -> int:
    """Add all not yet whitelisted addresses in `whitelist` to the whitelisted addresses in the auction contract.
    Returns the number of new whitelisted addresses"""

    if transaction_options is None:
        transaction_options = {}

    # only whitelist addresses that are not whitelisted yet
    filtered_whitelist = missing_whitelisted_addresses(auction_contract, whitelist)

    assert batch_size > 0
    chunks = [
        filtered_whitelist[i : i + batch_size]
        for i in range(0, len(filtered_whitelist), batch_size)
    ]

    for chunk in chunks:
        assert len(chunk) <= batch_size

        add_to_whitelist_call = auction_contract.functions.addToWhitelist(chunk)

        send_function_call_transaction(
            add_to_whitelist_call,
            web3=web3,
            transaction_options=transaction_options,
            private_key=private_key,
        )

        increase_transaction_options_nonce(transaction_options)

    return len(filtered_whitelist)


def missing_whitelisted_addresses(
    auction_contract: Contract, whitelist: Sequence[str]
) -> Sequence[str]:
    """
    Returns the addresses in `whitelist` which are not yet whitelisted in the auction contract
    """
    return [
        address
        for address in whitelist
        if not auction_contract.functions.whitelist(address).call()
    ]


class InvalidAddressException(Exception):
    pass


def validate_and_format_address(address):
    """Validates the address and formats it into the internal format
    Will raise `InvalidAddressException, if the address is invalid"""
    if is_address(address):
        return to_checksum_address(address)
    else:
        raise InvalidAddressException()


def read_whitelist(file_path: str):
    with open(file_path) as f:
        reader = csv.reader(f)
        addresses = []
        for line in reader:
            address = validate_and_format_address(line[0])
            addresses.append(address)
        return addresses
