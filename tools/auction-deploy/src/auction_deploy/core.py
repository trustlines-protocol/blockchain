from typing import Dict, NamedTuple, Optional, Sequence, Tuple

from deploy_tools.deploy import (
    deploy_compiled_contract,
    increase_transaction_options_nonce,
    load_contracts_json,
    send_function_call_transaction,
)
from web3.contract import Contract
from web3.exceptions import BadFunctionCallOutput

ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"


class AuctionOptions(NamedTuple):
    start_price: int
    auction_duration: int
    minimal_number_of_participants: int
    maximal_number_of_participants: int
    release_timestamp: int
    token_address: Optional[str] = None


class DeployedAuctionContracts(NamedTuple):
    locker: Contract
    slasher: Optional[Contract]
    auction: Contract


class DeployedContractsAddresses(NamedTuple):
    locker: Optional[str] = None
    slasher: Optional[str] = None
    auction: Optional[str] = None


def deploy_auction_contracts(
    *,
    web3,
    transaction_options: Dict = None,
    private_key=None,
    auction_options: AuctionOptions,
    already_deployed_contracts: DeployedContractsAddresses = DeployedContractsAddresses(),
) -> DeployedAuctionContracts:

    use_token = auction_options.token_address is not None

    if transaction_options is None:
        transaction_options = {}

    if (
        already_deployed_contracts.auction is not None
        and already_deployed_contracts.locker is None
    ):
        raise ValueError(
            "Cannot deploy new locker if auction already deployed due to constructor of auction."
        )

    compiled_contracts = load_contracts_json(__name__)

    deposit_locker_abi = (
        compiled_contracts["TokenDepositLocker"]["abi"]
        if use_token
        else compiled_contracts["ETHDepositLocker"]["abi"]
    )
    deposit_locker_bin = (
        compiled_contracts["TokenDepositLocker"]["bytecode"]
        if use_token
        else compiled_contracts["ETHDepositLocker"]["bytecode"]
    )

    validator_slasher_abi = compiled_contracts["ValidatorSlasher"]["abi"]
    validator_slasher_bin = compiled_contracts["ValidatorSlasher"]["bytecode"]

    auction_abi = (
        compiled_contracts["TokenValidatorAuction"]["abi"]
        if use_token
        else compiled_contracts["ETHValidatorAuction"]["abi"]
    )
    auction_bin = (
        compiled_contracts["TokenValidatorAuction"]["bytecode"]
        if use_token
        else compiled_contracts["ETHValidatorAuction"]["bytecode"]
    )

    if already_deployed_contracts.locker is not None:
        deposit_locker_contract = web3.eth.contract(
            abi=deposit_locker_abi,
            bytecode=deposit_locker_bin,
            address=already_deployed_contracts.locker,
        )
    else:
        deposit_locker_contract: Contract = deploy_compiled_contract(
            abi=deposit_locker_abi,
            bytecode=deposit_locker_bin,
            web3=web3,
            transaction_options=transaction_options,
            private_key=private_key,
        )
        increase_transaction_options_nonce(transaction_options)

    if already_deployed_contracts.slasher is not None:
        validator_slasher_contract = web3.eth.contract(
            abi=validator_slasher_abi,
            bytecode=validator_slasher_bin,
            address=already_deployed_contracts.slasher,
        )
    else:
        validator_slasher_contract = deploy_compiled_contract(
            abi=validator_slasher_abi,
            bytecode=validator_slasher_bin,
            web3=web3,
            transaction_options=transaction_options,
            private_key=private_key,
        )
        increase_transaction_options_nonce(transaction_options)

    if already_deployed_contracts.auction is not None:
        auction_contract = web3.eth.contract(
            abi=auction_abi,
            bytecode=auction_bin,
            address=already_deployed_contracts.auction,
        )
    else:
        auction_constructor_args: Tuple = (
            auction_options.start_price,
            auction_options.auction_duration,
            auction_options.minimal_number_of_participants,
            auction_options.maximal_number_of_participants,
            deposit_locker_contract.address,
        )
        if use_token:
            auction_constructor_args += (auction_options.token_address,)

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
    token_address=None,
    private_key=None,
) -> None:
    if transaction_options is None:
        transaction_options = {}

    if contracts.slasher is None:
        raise RuntimeError("Slasher contract not set")

    if not contracts.locker.functions.initialized().call():
        init_args: Tuple = (
            release_timestamp,
            contracts.slasher.address,
            contracts.auction.address,
        )
        if token_address is not None:
            init_args += (token_address,)

        deposit_init = contracts.locker.functions.init(*init_args)
        send_function_call_transaction(
            deposit_init,
            web3=web3,
            transaction_options=transaction_options,
            private_key=private_key,
        )
        increase_transaction_options_nonce(transaction_options)

    if not contracts.slasher.functions.initialized().call():
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

    compiled_contracts = load_contracts_json(__name__)

    auction_abi = compiled_contracts["BaseValidatorAuction"]["abi"]
    locker_abi = compiled_contracts["BaseDepositLocker"]["abi"]
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


def get_bid_token_address(web3, auction_address: str):
    compiled_contracts = load_contracts_json(__name__)
    auction_abi = compiled_contracts["TokenValidatorAuction"]["abi"]
    auction = web3.eth.contract(address=auction_address, abi=auction_abi)
    try:
        return auction.functions.bidToken().call()
    except BadFunctionCallOutput:
        # Thrown by web3 when function does not exist on contract
        return None


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
