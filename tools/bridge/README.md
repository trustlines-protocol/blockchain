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

As the bridge can be configured via environment variables, following the same
naming scheme as the [TOML configuration](#configuration), you can simply use an
`.env` file in the current directory. See the `.env.example` file as a first
example.

---

## Configuration

The bridge validator client can be configured in two different ways. Either by
a TOML configuration file or via environment variables. Both can also be
mixed, where the environment variables have priority. Environment variable names
are equal to the ones in the TOML file but in upper case (e.g. `HOME_RPC_URL`).
Special is the dot notation for [hierarchical options](#hierarchical-options).
The `--config` (`-c`) CLI parameter allows to define the path to the
configuration file.

There are tools which make working with a set of environment variables a more pleasant experience.
One of those is [dotenv](https://www.npmjs.com/package/dotenv-cli) which allows loading environment
variables from a `.env` file, an example of which is provided [here](.env.example). To start the
bridge with configuration from a `.env` file, run `dotenv tlbc-bridge`. Alternatively, you can
also use [envdir](https://pypi.org/project/envdir/).

The following table lists all available options. Configuration entries
with a default value are optional.

|                      Name                      |    Default    |                             Description                              |
| :--------------------------------------------: | :-----------: | :------------------------------------------------------------------: |
|               `foreign_rpc_url`                |               |  URL to JSON-RPC endpoint of foreign chain node [HTTP(S) protocol]   |
|                 `home_rpc_url`                 |               |    URL to JSON-RPC endpoint of home chain node [HTTP(S) protocol]    |
|             `foreign_rpc_timeout`              |     `180`     |  timeout option of the `web3` _HTTPProvider_ for the foreign chain   |
|               `home_rpc_timeout`               |     `180`     |    timeout option of the `web3` _HTTPProvider_ for the home chain    |
|        `foreign_chain_max_reorg_depth`         |     `10`      |     number of confirmation blocks required on the foreign chain      |
|          `home_chain_max_reorg_depth`          |      `1`      |       number of confirmation blocks required on the home chain       |
|     `foreign_chain_token_contract_address`     |               |          address of the token contract on the foreign chain          |
|       `foreign_bridge_contract_address`        |               |         address of the bridge contract on the foreign chain          |
|         `home_bridge_contract_address`         |               |           address of the bridge contract on the home chain           |
|      `foreign_chain_event_poll_interval`       |      `5`      |     interval in seconds to poll for new events on foreign chain      |
|        `home_chain_event_poll_interval`        |      `5`      |       interval in seconds to poll for new events on home chain       |
| `foreign_chain_event_fetch_start_block_number` |      `0`      | block number from which on events should be fetched on foreign chain |
|  `home_chain_event_fetch_start_block_number`   |      `0`      |  block number from which on events should be fetched on home chain   |
|             `home_chain_gas_price`             | `10000000000` |           gas price in GWei for confirmation transactions            |
|            `validator_private_key`             |               |      section of the validators private key to confirm transfers      |
|                   `logging`                    |               |               section to configure [logging](#logging)               |

### Hierarchical Options

When using hierarchical options like `logging` or `validator_private_key`, they
must be defined as TOML sections. For the configuration with environment
variables, the dot notation is supported. Therefore must each value contain its
whole upper hierarchy as keys separated with dots. Outside of an `.env` file
this will require the usage of the `env` command. The direct definition of a
variable with dotted names is likely to not work. Multiple further example can
be found within the following sections.

```toml
[logging.root]
level="DEBUG"
```

```sh
env LOGGING.ROOT.LEVEL="DEBUG" ... tlbc-bridge
```

### Private Key

The private key of the validator to confirm transfers can be provided in two
different ways. Either by its raw form as hex encoded string or in an encrypted
keystore with an additional password file. In case both are defined, the raw
version takes precedence.

A configuration via TOML file looks like that:

```toml
[validator_private_key]
raw = "0x..."
# or
keystore_path = "/path/to/keystore.json"
keystore_password_path = "/path/to/keystore_password"
```

A configuration via environment variables requires the following definitions:

```sh
VALIDATOR_PRIVATE_KEY.RAW="0x..."
# or
VALIDATOR_PRIVATE_KEY.KEYSTORE_PATH="/path/to/keystore.json"
VALIDATOR_PRIVATE_KEY.KEYSTORE_PASSWORD_PATH="/path/to/keystore_password"
```

### Logging

Logging can be configured globally or for specific components.

A configuration via TOML file looks like that:

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

A configuration via environment variables requires the following definitions:

```sh
LOGGING.ROOT.LEVEL="DEBUG"
LOGGING.LOGGERS.WEB3.LEVEL="INFO"
LOGGING.LOGGERS.URLLIB3.LEVEL="INFO"
```

Internally this is using _Python_'s
[logging.config.dictConfig](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig).
The exact schema for this key can be found at the [configuration dictionary
schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).

**Note:**
The dotted environment variable notation does not work everywhere. Values like
`[logging.loggers."bridge.main"]` are not representable and would get split.

### Validation

The configuration itself as well as the provided contracts and data will be verified at startup and continously. Make sure to check the logs for errors when running your validator node.

### Example

A minimal example configuration file for the current test deployment (_Ropsten_
to _Laika_) would look like this:

```toml
foreign_rpc_url = "http://localhost:8545"
home_rpc_url = "http://localhost:8546"

foreign_chain_token_contract_address = "0xCd7464985f3b5dbD96e12da9b018BA45a64256E6"
foreign_bridge_contract_address = "0x8d25a6C7685ca80fF110b2B3CEDbcd520FdE8Dd3"
home_bridge_contract_address = "0x77E0d930cF5B5Ef75b6911B0c18f1DCC1971589C"
foreign_chain_event_fetch_start_block_number = 6058407
home_chain_event_fetch_start_block_number = 3586854

[validator_private_key]
raw = "0x..."
```

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
