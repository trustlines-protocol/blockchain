# Trustlines Bridge Validator

This is the token bridge validator client for the _Trustlines_ chain.
The client connects to both networks of the bridge and observes token
transfer related events. The transfers on the foreign blockchain are then
confirmed on the home chain, providing the signature of the validator. A bridge
transfer requires at least 50% of all validators to be confirmed before it is payed
out. Already completed transfers are not confirmed again.

---

- [Basic Concept](#basic-concept)
- [Setup](#setup)
  - [Python Package Manager](#python-package-manager)
  - [Docker Image](#docker-image)
- [Configuration](#configuration)
  - [Validation](#validation)
  - [Logging](#logging)
  - [Example](#example)
- [Docker Compose](#docker-compose)
  - [Nodes Only](#nodes-only)
  - [Full Setup](#full-setup)

---

## Basic Concept

In its core, the bridge consists of two bridge contracts, one on each
blockchain, and an ERC20 Token on the foreign chain. The _Trustlines_ bridge is
unidirectional. It allows to transfer `TLN` (_Trustlines_ network token) from
the Ethereum mainnet (foreign chain) to the _Trustlines_ chain (home) as
native `TLC` (_Trustline_ coins). Therefore a dedicated
[ForeignBridge](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/bridge/ForeignBridge.sol)
contract gets deployed on the main chain. Token holders can then initiate
a transfer to this contract to trigger a bridge transfer. Tokens send to the
bridge are not recoverable and will be burned over time. Bridge validators are
obliged to observe the transfer events of the
[TrustlinesNetworkToken](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/token/TrustlinesNetworkToken.sol)
to the foreign bridge contract. They then confirm each transfer on the
[HomeBridgeContract](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/bridge/HomeBridge.sol)
on the _Trustlines_ chain with their signature. As soon as more than 50% of all
registered bridge validators have confirmed the same token transfer, the
`HomeBridge` initiates an internal transaction to release the `TLC`. To be able
to do so, the bridge contract gets initially funded. The recipient on the
_Trustlines_ chain is the same as the token sender on the main chain. The same
token transfer can not be payed out twice.

## Setup

Running a bridge validator requires in addition to this client two synchronized
nodes for the foreign (_Ethereum_ main chain) and home (_Trustlines_ chain)
network (see [configuration options](#configuration)). The bridge client
supports [light nodes](https://www.parity.io/what-is-a-light-client/). For
a more extended setup including these nodes, check out the
[section](#docker-compose) for `docker-compose` instructions.

### Python Package Manager

The bridge validator client is written in _Python_ can be installed with `pip`
directly.

```bash
pip install git+https://github.com/trustlines-protocol/blockchain.git#subdirectory=tools/bridge
```

The client can be started with the `tlbc-bridge` command, but needs
a [configuration](#configuration) to do so.

### Docker Image

The docker image needs to be built from the root directory of this repository.
The following example illustrates how to do so from the current directory
(`tools/bridge`).

```bash
docker build --file ./Dockerfile --tag tlbc-bridge ../../
```

---

## Configuration

The bridge validator client can be configured with a [TOML
configuration file](https://github.com/toml-lang/toml#spec), whose
path must be given via the `--config` (`-c`) CLI paramter.

Here is an example file with all possible entries. Optional entries
are listed with their default value.

```toml
[foreign_chain]
rpc_url = "http://localhost:8545"  # URL to the foreign chain's JSON RPC endpoint
rpc_timeout = 180                  # timeout for JSON RPC requests to the foreign chain node
max_reorg_depth = 1                # number of confirmation blocks required on the foreign chain
event_poll_interval = 5.0          # interval in seconds to poll for new events
event_fetch_start_block_number = 0 # block number from which on events should be fetched

# address of the foreign bridge contract:
bridge_contract_address = "0x8d25a6C7685ca80fF110b2B3CEDbcd520FdE8Dd3"
# address of the TLN token contract
token_contract_address = "0xCd7464985f3b5dbD96e12da9b018BA45a64256E6"

[home_chain]
rpc_url = "http://localhost:8546"  # URL to JSON-RPC endpoint of home chain node [HTTP(S) protocol]
rpc_timeout = 180                  # timeout for JSON RPC requests to the foreign chain node
max_reorg_depth = 10               # number of confirmation blocks required on the home chain
event_poll_interval = 5.0          # interval in seconds to poll for new events
event_fetch_start_block_number = 0 # block number from which on events should be fetched on home chain
gas_price = 10000000000            # gas price in Wei for confirmation transactions (default 10 GWei)
minimum_validator_balance = 40000000000000000
balance_warn_poll_interval = 60.0
max_pending_transactions_per_block = 16 # maximum number of pending transaction per reorg-unsafe block

# address of the home bridge contract
bridge_contract_address = "0x77E0d930cF5B5Ef75b6911B0c18f1DCC1971589C"

[validator_private_key]
# Configure the private key of the validator to be used. Either specify
# the decrypted key in hex encoded format in the field 'raw'...
raw = "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
# .. or alternatively specify a path to a keystore and password file:
keystore_path = "/path/to/validator_keystore.json"
keystore_password_path = "/path/to/password-file"

[webservice]
enabled = false            # enables or disables the webservice
host = "127.0.0.1"         # hostname or IP address the webservice should listen on
port = 8640                # port number the webservice should listen on
```

### Logging

Logging can be configured globally or for specific components in the
config file under the `logging` section.

A configuration may look like that:

```toml
[logging.root]
level = "DEBUG"

[logging.loggers."bridge.main"]
level = "DEBUG"

# web3 is too verbose with level debug
[logging.loggers.web3]
level = "INFO"

[logging.loggers.urllib3]
level = "INFO"
```

Internally this is using _Python_'s
[logging.config.dictConfig](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig).
The exact schema for this key can be found at the [configuration dictionary
schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).

The logging configuration can be changed at runtime. If you send a
SIGHUP signal to the tlbc-bridge program, it will re-read the
configuration file and apply the changed logging settings. Please be
aware that this is the only part of the configuration that is being
reloaded. Changing other values does not have any effect on the
running program.

### Webservice

The webservice allows to query information about the current state of the bridge node. It is not
running by default and must be enabled in the config file if desired:

```toml
[webservice]
enabled = true             # false by default
host = "127.0.0.1"         # hostname or IP address the webservice should listen on
port = 8640                # port number the webservice should listen on
```

### Validation

The configuration itself as well as the provided contracts and data will be verified at startup and continously. Make sure to check the logs for errors when running your validator node.

## Docker Compose

Using the provided configuration files for `docker-compose` (at `./docker`)
allows an easy setup including the blockchain nodes. Make sure
you checked out the section regarding the [docker setup](#docker-image).

### Full Setup

Running the whole bridge validator setup with all components via
`docker-compose` requires a complete configuration environment file (`.env`). To
switch between the different setup environments, exchange the `docker-compose`
configuration file postfix by `development` or `production`. For the
production setup the `build` does nothing and can be skipped.

```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose-base.yaml --file ./docker/docker-compose-development.yaml build
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose-base.yaml --file ./docker/docker-compose-development.yaml up
```

**Note: There is no production Trustlines chain yet!**

### Nodes Only

This approach is useful when it is intended to run the bridge client as
a standalone application on your machine (see [pip
install](#python-package-manager)). In contrast to the previous full setup the
configuration via environment file is not necessary and has no effect.

```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose-base.yaml --file ./docker/docker-compose-development.yaml up node_foreign node_home
```

The JSON-RPC endpoint of the foreign chain is linked to `http://localhost:8545`.
The home chain can be connected via `http://localhost:8546`.
