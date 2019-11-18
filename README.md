# Trustlines Blockchain

- [The Trustlines Blockchain Infrastructure](#the-trustlines-blockchain-infrastructure)
  - [Networks](#networks)
  - [System Requirements](#system-requirements)
  - [Security](#security)
  - [Setup With the Quickstart Script](#setup-with-the-quickstart-script)
  - [Setup With Docker](#setup-with-docker)
    - [Blockchain Node](#blockchain-node)
    - [Netstats Client](#netstats-client)
    - [Monitor](#monitor)
    - [Bridge](#bridge)
  - [Setup Without Docker](#setup-without-docker)
- [Development](#development)
  - [Build Own Image](#build-own-image)
  - [Upload Image](#upload-image)
  - [Running Tests on Contracts](#running-tests-on-contracts)

## The Trustlines Blockchain Infrastructure

Nodes of the Trustlines Blockchain run various applications:

- The node of the blockchain itself
- The monitor that checks if validators act honestly (optional)
- The bridge between Ethereum and the Trustlines Blockchain (only run by validators)
- The netstats client to report the node state to `https://netstats.trustlines.foundation`(optional)

There are multiple ways to set each of these up. The most straightforward one by far is via our interactive quickstart
script. Finer control can be achieved by starting the components individually as Docker containers. Finally, it is also
possible to avoid Docker altogether and run everything directly on the host machine.

Before starting the installation process, please have a look at the system requirements and the note on security.

### Networks

There are two blockchain networks related to this project. The test network is
called Laika. The productive network is called the Trustlines Blockchain. Often
this gets abbreviated to `tlbc`, especially for technical components. The
instructions within this documentation primarily focus on the Trustlines
Blockchain.

### System Requirements

Based on the experiences we have had on our long-running testnet Laika, we recommend at least 4GB of memory and 20GB of SSD
storage.

Validators should make sure their node has a high uptime: Otherwise, they miss out on potential revenue and harm the
network by increasing average block intervals and time to finality.

For block validation and creation, it is essential to make sure your host system has the correct time configuration. On
most systems, this should be the case by default. You can check the settings with `timedatectl` (look for
`"System clock synchronized: yes"`). For more information, see for example the corresponding
[Ubuntu help page](https://help.ubuntu.com/lts/serverguide/NTP.html).

For the quickstart and Docker installation modes, [Docker](https://docker.com) needs to be installed and configured.
Please refer to the official documentation and make sure your user is added to the `docker` user group if you cannot
access root permissions to run containers.

### Security

For validators it is crucial to safely back up their private key. If they lose their key, they will not be able to

- create any blocks or earn block rewards or
- withdraw their stake on the main chain once it is unlocked.

Furthermore, it is advisable to keep the amount of funds stored in the validator account small by regularly sending the
newly earned income to a different account (e.g., a cold wallet stored on a different machine).

### Setup With the Quickstart Script

The quickstart script will set up the blockchain node and the monitor as well as optionally the bridge and netstats
clients. It allows importing a private key in order to act as a validator. In addition, it will start a
[watchtower](https://hub.docker.com/r/containrrr/watchtower) to automatically update the Docker containers when newer versions
become available (e.g. for bug fixes or network forks).

To fetch and run the most recent version of the quickstart script for the Trustlines Blockchain, execute the following command on your machine:

```sh
bash <(curl -L quickstart.tlbc.trustlines.foundation)
```

If you want a quickstart setup for the Laika testnet, use the following command instead:

```sh
bash <(curl -L quickstart.laika.trustlines.foundation)
```

The script is interactive and will ask you which components to set up. Once the
setup is complete, the various components will run in the background in the form
of Docker containers. Configuration and chain data can be found in the
`tlbc` directory placed in the current working directory (`trustlines` in case of a Laika setup). It is possible
to customize the own setup by editing those configuration files. This goes for
the configuration of the different components, as well as the composition of the
Docker containers. If an optional component has not been set up on an earlier
run, it can be added later by executing the quickstart script again.

Executing the script again is safe: No configuration will be overridden without
asking, in case the user has changed them itself. If conflicting configuration
updates occur, they are shown to the user who can ask to see a diff of the
changes.

### Setup With Docker

A more explicit way of setting up the various components is starting the Docker containers manually as described here.
To keep commands as concise as possible, only the most basic options are provided. You might want to set additional
ones, e.g., container names or restart policies.

Alternatively, you could also use the quickstart script and adjust the setup afterwards with commands similar to the
following ones.

#### Blockchain Node

The blockchain image is a standard Parity client with a custom configuration for the Trustlines Blockchain. It also
accepts a few additional command line options as described in the help message:

```
$ docker run --rm trustlines/tlbc-node:release --help


 NAME
   Parity Wrapper

 SYNOPSIS
   parity_wrapper.sh [-r] [role] [-a] [address] [-p] [arguments]

 ...
```

Before starting the node, create a Docker network to conveniently allow other containers to easily connect to it:

```sh
$ docker network create network-tlbc
```

When running the node, you typically want to forward necessary ports to the host so that Parity can find and connect to
peers. Additionally, you might want to mount some volumes to persist configuration and chain data. For instance, to run
a non-validator node:

```sh
$ mkdir -p tlbc/databases/tlbc tlbc/config tlbc/enode tlbc/shared
$ docker run -d --name tlbc-node --network network-tlbc \
    -v $(pwd)/tlbc/databases/tlbc:/data \
    -v $(pwd)/tlbc/config:/config/custom \
    -v $(pwd)/tlbc/enode:/config/network \
    -v $(pwd)/tlbc/shared:/shared/ \
    -p 30300:30300 -p 30300:30300/udp \
    trustlines/tlbc-node:release
```

If you are a validator, this sequence of commands will supply Parity with your keystore file, password, and address so
that it can produce blocks:

```sh
$ mkdir -p tlbc/databases/tlbc tlbc/config/keys/tlbc tlbc/enode tlbc/shared
$ cp /path/to/your/keystore/file.json tlbc/config/keys/tlbc/account.json
$ echo "<passphrase_for_keystore_file>" > tlbc/config/pass.pwd
$ docker run -d --name tlbc-node --network network-tlbc \
    -v $(pwd)/tlbc/databases/tlbc:/data \
    -v $(pwd)/tlbc/config:/config/custom \
    -v $(pwd)/tlbc/enode:/config/network \
    -v $(pwd)/tlbc/shared:/shared/ \
    -p 30300:30300 -p 30300:30300/udp \
    trustlines/tlbc-node:release
```

#### Netstats Client

The netstats client reports the state of your node to the
[netstats page](https://netstats.tlbc.trustlines.foundation/) that gives a rough overview of the current network state.
It is an optional component which helps the community by providing information on your running node to a central server.

To participate, you first need to request credentials managed by the Trustlines Foundation. Please email
`netstats@trustlines.foundation` to do so.

Once you have your credentials, create a file `tlbc/netstats-env` with the following contents:

```sh
WS_USER=username-as-provided-by-the-foundation
WS_PASSWORD=password-as-provided-by-the-foundation
INSTANCE_NAME=please-choose-a-nice-name-here
```

If you want to be publicly displayed as a validator, add the following line at the end:

```sh
HIDE_VALIDATOR_STATUS=false
```

Now, the netstats client can be started with

```sh
$ docker run -d --name netstats-client --network network-tlbc \
    --env-file tlbc/netstats-env \
    -e RPC_HOST=tlbc-node \
    -e RPC_PORT=8545 \
    trustlines/netstats-client:release
```

#### Monitor

The monitor watches the blockchain and makes sure that validators are online and do not equivocate. Every node in the
network should run it and users should regularly check for reports of misbehaving validators.

Assuming the blockchain node was configured as described above, this command will start the monitor:

```sh
$ mkdir -p tlbc/monitor/reports tlbc/monitor/state
$ docker run -d --name tlbc-monitor --network network-tlbc \
    -v $(pwd)/tlbc/shared:/config \
    -v $(pwd)/tlbc/monitor/state:/state \
    -v $(pwd)/tlbc/monitor/reports:/reports \
    trustlines/tlbc-monitor:release \
    -c /config/trustlines-spec.json -r /reports -d /state \
    -u http://tlbc-node:8545
```

#### Bridge

Validators of the Trustlines Blockchain have to run the bridge that converts TLN tokens on the Ethereum chain to TLC
tokens on the Trustlines Blockchain. Non-validators should not run a bridge node.

The bridge requires an Ethereum mainnet node which can be a light client. To start one, execute

```sh
$ docker network create network-ethereum
$ mkdir -p tlbc/databases/mainnet
$ docker run -d --name mainnet-node --network network-ethereum \
    -v $(pwd)/tlbc/databases/mainnet:/data/database \
    --user root \
    ethereum/client-go:stable \
    --rpc --rpcaddr 0.0.0.0 --nousb --ipcdisable --syncmode light \
    --datadir /data/database --rpccorsdomain * --rpcvhosts=*
```

Now, write a configuration file for the bridge node and store it in `tlbc/bridge-config.toml`:

```
[foreign_chain]
rpc_url = "http://mainnet-node:8545"
token_contract_address = "0x679131F591B4f369acB8cd8c51E68596806c3916"
bridge_contract_address = "0x18BDC736b23Ff7294BED9fa988a1443357C7B0ed"
event_fetch_start_block_number = 8932341

[home_chain]
rpc_url = "http://tlbc-node:8545"
bridge_contract_address = "0x0000000000000000000000000000000000000401"
event_fetch_start_block_number = 0

[validator_private_key]
keystore_path = "/config/keys/tlbc/account.json
keystore_password_path = "/config/pass.pwd"
```

Note that the keystore path is not an actual path on the host machine, but rather in the bridge container.
The container will have to connect to both of the Docker networks and access the config directory.
Therefore, the command looks like this:

```sh
$ docker run -d --name bridge-client --network network-tlbc --network network-ethereum \
    -v $(pwd)/tlbc/config:/config \
    -v $(pwd)/tlbc/bridge-config.toml:/config/bridge-config.toml \
    trustlines/bridge:release \
    -c /config/bridge-config.toml
```

### Setup Without Docker

We refer to the documentation of the individual components:

- [Parity](https://wiki.parity.io/Parity-Ethereum)
- [Netstats](https://github.com/trustlines-protocol/ethstats-client)
- [Monitor](https://github.com/trustlines-protocol/tlbc-monitor)
- [Bridge](https://github.com/trustlines-protocol/blockchain/tree/master/tools/bridge)

For the Laika node, make sure it uses the correct [chain spec file](), that the right TCP and UDP ports are used
(30300), and that the JSON RPC APIs `web3`, `eth`, and `net` are enabled.

## Development

### Build Own Image

To build the _Docker_ image, checkout this repository and run `docker build` with your preferred tag name. As the context of
the build must be the project root, the path to the `Dockerfile` has to be specified manually.

```sh
$ git clone https://github.com/trustlines-protocol/blockchain
$ docker build -f chain/laika/Dockerfile -t MY_TAGNAME .
$ docker run ... MY_TAGNAME ...
```

### Running Tests on Contracts

First, install the solidity compiler `solc` for compiling the contracts.
You can follow the [official installation documentation](https://solidity.readthedocs.io/en/v0.4.24/installing-solidity.html).
dependencies, compile the contracts and run the tests.

## access.laika.trustlines.foundation

The Trustlines Foundation hosts a publically accessible node for the
Laika Testnet.

You can access it via the following URL:
https://access.laika.trustlines.foundation
