import os

CONFIG_DIR = "config"
ENODE_DIR = "enode"
DATABASE_DIR = "databases"
KEY_DIR = os.path.join(CONFIG_DIR, "keys")

KEYSTORE_FILE_NAME = "account.json"
PASSWORD_FILE_NAME = "pass.pwd"

PASSWORD_FILE_PATH = os.path.join(CONFIG_DIR, PASSWORD_FILE_NAME)
ADDRESS_FILE_PATH = os.path.join(CONFIG_DIR, "address")

NETSTATS_ENV_FILE_PATH = "netstats-env"

BRIDGE_CONFIG_FILE_EXTERNAL = "bridge-config.toml"
BRIDGE_CONFIG_DEFAULT_FOREIGN_RPC = "http://foreign-node:8545"
BRIDGE_DOCUMENTATION_URL = (
    "https://github.com/trustlines-protocol/blockchain/tree/master/tools/bridge"
)

MONITOR_DIR = "monitor"
MONITOR_REPORTS_DIR = os.path.join(MONITOR_DIR, "reports")

SHARED_CHAIN_SPEC_PATH = "shared/trustlines-spec.json"
