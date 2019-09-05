from pathlib import Path

import click

from quickstart.constants import (
    BRIDGE_CONFIG_FILE_EXTERNAL,
    BRIDGE_CONFIG_FOREIGN_BRIDGE_CONTRACT_ADDRESS,
    BRIDGE_CONFIG_FOREIGN_RPC_URL,
    BRIDGE_CONFIG_FOREIGN_START_BLOCK_NUMBER,
    BRIDGE_CONFIG_FOREIGN_TOKEN_CONTRACT_ADDRESS,
    BRIDGE_CONFIG_HOME_BRIDGE_CONTRACT_ADDRESS,
    BRIDGE_CONFIG_HOME_RPC_URL,
    BRIDGE_CONFIG_HOME_START_BLOCK_NUMBER,
    BRIDGE_CONFIG_KEYSTORE_PASSWORD_PATH,
    BRIDGE_CONFIG_KEYSTORE_PATH,
    BRIDGE_DOCUMENTATION_URL,
)
from quickstart.utils import is_bridge_prepared

ENV_FILE_TEMPLATE = """\
[foreign_chain]
rpc_url = '{foreign_rpc_url}'
token_contract_address = '{foreign_token_contract_address}'
bridge_contract_address = '{foreign_bridge_contract_address}'
event_fetch_start_block_number = {foreign_start_block_number}

[home_chain]
rpc_url = '{home_rpc_url}'
bridge_contract_address = '{home_bridge_contract_address}'
event_fetch_start_block_number = {home_start_block_number}

[validator_private_key]
keystore_path = '{keystore_path}'
keystore_password_path = '{keystore_password_path}'
"""


def setup_interactively() -> None:
    if is_bridge_prepared():
        click.echo("You have already set the bridge client up.\n")
        return

    click.echo(
        "\nWe can set a validator bridge client up that confirms bridge transfers. "
        "Doing so requires an additional node syncing the Ethereum mainnet. "
        "This node will run in light mode to use as little resource as "
        "possible. Checkout the following link for more information on how the bridge "
        f"works:\n{BRIDGE_DOCUMENTATION_URL}\nThis setup will reuse the keystore "
        "of the validator node.\n"
    )
    if not click.confirm(
        "Do you want to set the bridge client up? (highly recommended)", default=True
    ):
        # Necessary to make docker-compose not complaining about it.
        Path(BRIDGE_CONFIG_FILE_EXTERNAL).touch()
        return

    env_file_content = ENV_FILE_TEMPLATE.format(
        foreign_rpc_url=BRIDGE_CONFIG_FOREIGN_RPC_URL,
        home_rpc_url=BRIDGE_CONFIG_HOME_RPC_URL,
        foreign_token_contract_address=BRIDGE_CONFIG_FOREIGN_TOKEN_CONTRACT_ADDRESS,
        foreign_bridge_contract_address=BRIDGE_CONFIG_FOREIGN_BRIDGE_CONTRACT_ADDRESS,
        foreign_start_block_number=BRIDGE_CONFIG_FOREIGN_START_BLOCK_NUMBER,
        home_bridge_contract_address=BRIDGE_CONFIG_HOME_BRIDGE_CONTRACT_ADDRESS,
        home_start_block_number=BRIDGE_CONFIG_HOME_START_BLOCK_NUMBER,
        keystore_path=BRIDGE_CONFIG_KEYSTORE_PATH,
        keystore_password_path=BRIDGE_CONFIG_KEYSTORE_PASSWORD_PATH,
    )

    with open(BRIDGE_CONFIG_FILE_EXTERNAL, "w") as env_file:
        env_file.write(env_file_content)
    click.echo("Bridge client setup complete.")
