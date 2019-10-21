import os

CONFIG_DIR = "config"
ENODE_DIR = "enode"
DATABASE_DIR = "databases"
KEY_DIR = os.path.join(CONFIG_DIR, "keys", "Trustlines")

KEYSTORE_FILE_NAME = "account.json"
PASSWORD_FILE_NAME = "pass.pwd"

KEYSTORE_FILE_PATH = os.path.join(KEY_DIR, KEYSTORE_FILE_NAME)
PASSWORD_FILE_PATH = os.path.join(CONFIG_DIR, PASSWORD_FILE_NAME)
ADDRESS_FILE_PATH = os.path.join(CONFIG_DIR, "address")

NETSTATS_ENV_FILE_PATH = "netstats-env"
NETSTATS_SERVER_LAIKA_BASE_URL = "https://laikanetstats.trustlines.foundation/"

BRIDGE_CONFIG_FILE_EXTERNAL = "bridge-config.toml"
BRIDGE_DOCUMENTATION_URL = (
    "https://github.com/trustlines-protocol/blockchain/tree/master/tools/bridge"
)

MONITOR_DIR = "monitor"
MONITOR_REPORTS_DIR = os.path.join(MONITOR_DIR, "reports")

SHARED_CHAIN_SPEC_PATH = "shared/trustlines-spec.json"
