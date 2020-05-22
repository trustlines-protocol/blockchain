# fmt: off
# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses for the validator auction in one transaction
# This needs to be at the top of external imports when imported modules import eth_tester themselves
import eth_tester; assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6; eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6  # noqa: E402, E702 isort:skip
# fmt: on

import json
import os

import pytest
from deploy_tools.cli import test_json_rpc
from deploy_tools.deploy import deploy_compiled_contract, load_contracts_json
from eth_keyfile import create_keyfile_json
from eth_utils import to_canonical_address

from auction_deploy.core import AuctionOptions

RELEASE_TIMESTAMP_OFFSET = 3600 * 24 * 180


def remove_click_options_environment_variables():
    """Remove the environment variables used by click options in the CLI.
    Otherwise they will interfere with the tests.
    Mark that environment variables related to options provided by the deploy
    tools are already removed due to the plugin.
    """
    for env_var in list(os.environ.keys()):
        if env_var.startswith("AUCTION_DEPLOY_"):
            del os.environ[env_var]


remove_click_options_environment_variables()


def create_address_string(i: int):
    return f"0x{str(i).rjust(40, '0')}"


@pytest.fixture()
def keystores(tmp_path, account_keys, key_password):
    """paths to keystore files"""
    paths = []
    for i, private_key in enumerate(account_keys[:2]):
        file_path = tmp_path / f"keyfile-{i}.json"
        file_path.write_text(
            json.dumps(
                create_keyfile_json(
                    private_key.to_bytes(), key_password.encode("utf-8")
                )
            )
        )
        paths.append(file_path)

    return paths


@pytest.fixture()
def keystore_file_path(tmp_path, keystores, key_password):
    """path to keystore of account[1]"""
    return keystores[1]


@pytest.fixture()
def key_password():
    """password used for the keystores"""
    return "test_password"


@pytest.fixture()
def private_key(account_keys):
    """private key of account[1]"""
    return account_keys[1]


@pytest.fixture()
def whitelist():
    return [to_canonical_address(create_address_string(i)) for i in range(30)]


@pytest.fixture
def ether_owning_whitelist(accounts):
    return [accounts[1], accounts[2]]


@pytest.fixture
def release_timestamp(web3):
    """release timestamp used for DepositLocker contract"""
    now = web3.eth.getBlock("latest").timestamp
    return now + RELEASE_TIMESTAMP_OFFSET


@pytest.fixture()
def token_contract(ether_owning_whitelist):
    contract_assets = load_contracts_json("auction_deploy")
    abi = contract_assets["TrustlinesNetworkToken"]["abi"]
    bytecode = contract_assets["TrustlinesNetworkToken"]["bytecode"]
    token_name = "Trustlines Network Token"
    token_symbol = "TLN"
    token_decimal = 18
    number_to_mint = 10 * 10 ** 18
    premint_address = ether_owning_whitelist[0]
    constructor_args = (
        token_name,
        token_symbol,
        token_decimal,
        premint_address,
        number_to_mint,
    )

    token_contract = deploy_compiled_contract(
        abi=abi,
        bytecode=bytecode,
        web3=test_json_rpc,
        constructor_args=constructor_args,
    )
    token_contract.functions.transfer(
        ether_owning_whitelist[1], int(number_to_mint / 2)
    ).transact({"from": ether_owning_whitelist[0]})

    return token_contract


@pytest.fixture(params=["Eth auction", "Token auction"])
def use_token(request):
    if request.param == "Eth auction":
        return False
    return True


@pytest.fixture()
def auction_options(release_timestamp, use_token, token_contract):
    start_price = 1
    auction_duration = 2
    minimal_number_of_participants = 1
    maximal_number_of_participants = 2
    token_address = token_contract.address if use_token else None

    contract_options = AuctionOptions(
        start_price=start_price,
        auction_duration=auction_duration,
        minimal_number_of_participants=minimal_number_of_participants,
        maximal_number_of_participants=maximal_number_of_participants,
        release_timestamp=release_timestamp,
        token_address=token_address,
    )

    return contract_options
