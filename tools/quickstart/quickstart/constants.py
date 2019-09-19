import os

BASE_DIR = "trustlines"  # Relative to the current working directory
CONFIG_DIR = os.path.join(BASE_DIR, "config")
ENODE_DIR = os.path.join(BASE_DIR, "enode")
DATABASE_DIR = os.path.join(BASE_DIR, "databases")
KEY_DIR = os.path.join(CONFIG_DIR, "keys", "Trustlines")

KEYSTORE_FILE_NAME = "account.json"
PASSWORD_FILE_NAME = "pass.pwd"

KEYSTORE_FILE_PATH = os.path.join(KEY_DIR, KEYSTORE_FILE_NAME)
PASSWORD_FILE_PATH = os.path.join(CONFIG_DIR, PASSWORD_FILE_NAME)
ADDRESS_FILE_PATH = os.path.join(CONFIG_DIR, "address")

NETSTATS_ENV_FILE_PATH = os.path.join(BASE_DIR, "netstats-env")
NETSTATS_SERVER_BASE_URL = "https://laikanetstats.trustlines.foundation/"

BRIDGE_CONFIG_FILE_EXTERNAL = os.path.join(BASE_DIR, "bridge-config.toml")
BRIDGE_CONFIG_DIR_INTERNAL = "/config"
BRIDGE_CONFIG_FOREIGN_RPC_URL = "http://mainnet.node:8545"
BRIDGE_CONFIG_HOME_RPC_URL = "http://laika-testnet.node:8545"
BRIDGE_CONFIG_FOREIGN_TOKEN_CONTRACT_ADDRESS = (
    "0x54B06531214AD41DE9d771c10C0030d048d0cC67"
)
BRIDGE_CONFIG_FOREIGN_BRIDGE_CONTRACT_ADDRESS = (
    "0x2171Dd4d4F6ca30FeEA8a27b96257A67f371d87A"
)
BRIDGE_CONFIG_FOREIGN_START_BLOCK_NUMBER = 1321331
BRIDGE_CONFIG_HOME_BRIDGE_CONTRACT_ADDRESS = (
    "0x854dF872BB8bfECafFB1077FCfd7aa0B7C838A60"
)
BRIDGE_CONFIG_HOME_START_BLOCK_NUMBER = 4153205
BRIDGE_CONFIG_KEYSTORE_PATH = os.path.join(
    BRIDGE_CONFIG_DIR_INTERNAL, "keys", "Trustlines", KEYSTORE_FILE_NAME
)
BRIDGE_CONFIG_KEYSTORE_PASSWORD_PATH = os.path.join(
    BRIDGE_CONFIG_DIR_INTERNAL, PASSWORD_FILE_NAME
)
BRIDGE_DOCUMENTATION_URL = (
    "https://github.com/trustlines-protocol/blockchain/tree/master/tools/bridge"
)
