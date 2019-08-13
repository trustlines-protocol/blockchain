# Trustlines Bridge Validator

This is a client for validators of the token bridge to the _Trustlines_ chain.
The client connects two the both networks of the bridge and observes token
transfer related events. The made transfers on the foreign blockchain get then
confirmed on the home chain, providing the signature of the validator. A bridge
transfer requires at least 50% of all validators to confirm before it gets payed
out. Already completed transfers are not confirmed anymore.

---

- [Basic Concept](#basic-concept)
- [Setup](#setup)
  - [Python Package Manager](#python-package-manager)
  - [Makefile](#make-file)
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
blockchain, and a token on one of both. The _Trustlines_ bridge is
unidirectional. It allows to transfer `TLN` (_Trustlines_ network token) from
the Ethereum main network (foreign chain) to the _Trustlines_ chain (home) as
native `TLC` (_Trustline_ coins). Therefore a dedicated
[ForeignBridge](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/bridge/ForeignBridge.sol)
contract gets deployed on the main chain. Token holders can then initiate
a transfer to this contract to trigger a bridge transfer. Tokens send to the
bridge are not recoverable and will be burned over time. Bridge validators are
obliged to observe the transfer events of the
[TrustlinesNetworkToken](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/token/TrustlinesNetworkToken.sol)
to the foreign bridge contract. Doing so, they confirm such transfer at the
[HomeBridgeContract](https://github.com/trustlines-protocol/blockchain/blob/master/contracts/contracts/bridge/HomeBridge.sol)
on the _Trustlines_ chain with their signature. As soon as over 50% of all
registered bridge validators have confirmed the same token transfer, the
`HomeBridge` do an internal transaction to release the `TLC`. Therefore the
bridge contract gets initially funded. The recipient of the transfer on the
_Trustlines_ chain is the same as the token sender on the main chain. The same
token transfer can not be payed out twice.

## Setup

Running a bridge validator requires in addition to this client two syncing nodes
for the foreign (_Ethereum_ main chain) and home (_Trustlines_ chain) network
(see [configuration options](#configuration)). The bridge client supports the usage
with nodes having the [light
mode](https://www.parity.io/what-is-a-light-client/) activated. This saves
many resources, especially for the main network. For a more extended setup
including such nodes, checkout the [section](#docker-compose) for
`docker-compose` instructions.

### Python Package Manager

The bridge validator client is written in _Python_ can be installed with `pip`
directly.

```bash
pip install git+https://github.com/trustlines-protocol/blockchain.git#subdirectory=tools/bridge
```

Afterwards the client can be started with the `tlbc-bridge` command. But it will
not run successfully without any [configuration](#configuration). Therefore have
a look in the related section.

### Makefile

Alternatively you can checkout this repository locally and use the `Makefile` to
install the bridge client. This approach is the go for solution when intend to
work in more detail with the implementation.

```bash
git clone https://github.com/trustlines-protocol/blockchain.git
cd blockchain/tools/bridge
make install
```

Afterwards the client can be started with `make start`. It must be configured in
the same way as the [pip install](#python-package-manager) approach.

### Docker Image

The docker image needs to be built from the root directory of this repository.
The following example illustrates how to do so from the current directory
(`tools/bridge`).

```bash
docker build --file ./Dockerfile --tag tlbc-bridge ../../
```

To avoid the cumbersome injection of a configuration file, the easier approach is
to use environment variables. Therefore an `.env` file in the current directory
looks most-likely the same as the TOML configuration file. According to the
[configuration](#configuration) section the option names must be written in
upper case. Afterwards the client in the _Docker_ container will make use of
these values automatically. Make sure to checkout the `.env.example` file as
first template.

---

## Configuration

The bridge validator client can be configured in two different ways. Either by
a TOML configuration file or via environment variables. Both can also be
mixed, where the environment variables have priority. Environment variable names
are equal to the ones in the TOML file but in upper case (e.g. `HOME_RPC_URL`).
The `--config` (`-c`) CLI parameter allows to define the path to such
configuration file.

The following table illustrates all available options. Configuration entries
with a default value are optional to set.

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
|            `validator_private_key`             |               |    HexString as private key of the validator to confirm transfers    |
|                   `logging`                    |               |             dictionary to configure [logging](#logging)              |

### Logging

The following presents how to configure the logging of the client by setting the
`logging` key in the TOML configuration file:

```toml
[logging.root]
level = "INFO"

[logging.loggers."bridge.main"]
level = "DEBUG"
```

Internally this is using _Python_ its
[logging.config.dictConfig](https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig).
The exact schema for this key can be read at the [configuration dictionary
schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema).

### Validation

The bridge client has a quite exhaustive validation of the configuration. Next
to usual syntactic checks, additional semantic verification has been
implemented. Doing so it should be hard to start a wrongly configured client
without noticing it or getting not well understandable exceptions at a later
point.<br>
So it will be verified that the contract addresses do point to actual contracts
on the respective blockchain. Furthermore it will be verified if these contracts
support the necessary minimal ABI, like the to observe events.<br>
Moreover it is checked if the address of the configured private key is
an authorized bridge validator at the point of time. While other validation
issues stop the client at the very beginning, an unauthorized validator key
only log warnings and do not confirm transfers. This is meant to allow bridge
validators to start their node already before they become authorized and also
after they have been removed.

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

validator_private_key = "0x0dd4f8fa8a0cf333cdea89058bb8e280bfa14f2d011ececba2d8dce38d7d2668"
```

## Docker Compose

Using the provided configuration files for `docker-compose` (at `./docker`)
brings the advantage of an easy setup including the blockchain nodes. Make sure
you checked out the section regarding the [docker setup](#docker-image) to be
well prepared.

### Nodes Only

This approach is useful, when you intend to run the bridge client as plain
application on your machine (see [pip](#python-package-manager) and
[Makefile](#makefile) setup). To switch between the test and production setup,
exchange the `docker-compose` configuration file postfix with `development` or
`production`.

```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose-nodes-production.yml up
```

The JSON-RPC endpoint of the node for the foreign chain is linked to
`http://localhost:8545`. The home chain can be connected via
`http://localhost:8546`.

### Full Setup

Running the whole bridge validator setup with all components by a `docker-compose`.
This assumes a correct configuration via an environment file (`.env`).

```bash
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml build
docker-compose --project-name tlbc-bridge --file ./docker/docker-compose.yml --file ./docker/docker-compose-nodes-production.yml up
```

**There is no production Trustlines chain yet!**
