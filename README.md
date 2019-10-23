# Trustlines Blockchain

- [The Trustlines Blockchain Infrastructure](#the-trustlines-blockchain-infrastructure)
  - [System Requirements](#system-requirements)
  - [Backups](#backups)
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
- The monitor that checks if validators act honestly
- The bridge between Ethereum and the Trustlines Blockchain (only run by validators)
- The netstats client to report the node state to `https://netstats.trustlines.foundation`(optional)

There are multiple ways to set each of these up. The most straightforward one by far is via our interactive quickstart
script. Finer control can be achieved by starting the components individually as Docker containers. Finally, it is also
possible to avoid Docker altogether and run everything directly on the host machine.

Before starting the installation process, please have a look at the system requirements and the note on backups.

### System Requirements

Based on the experiences we have had on our long-running testnet, we recommend at least 2GB of memory and 10GB of SSD
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

### Backups

For validators it is crucial to safely back up their private key.

### Setup With the Quickstart Script

The quickstart script will set up the blockchain node and the monitor as well as optionally the bridge and netstats
clients. It allows importing a private key in order to act as a validator. In addition, it will start a
[watchtower](https://hub.docker.com/r/containrrr/watchtower) to automatically update the containers when newer versions
become available (e.g. for bug fixes or network forks).

To fetch the most recent version of the quickstart script and run it, execute the following command on your machine:

```sh
$ wget -O quickstart.sh https://github.com/trustlines-protocol/blockchain/raw/master/quickstart.sh && bash quickstart.sh
```

The script is interactive and will ask you which components to set up. Once the setup is complete, the various
components will run in the background in the form of Docker containers. Configuration and chain data can be found in
the `trustlines` directory placed in the current working directory.

Executing the script again is safe: No configuration will be overridden. This allows you to add components not
configured in earlier runs and will restart all containers.

### Setup With Docker

A more explicit way of setting up the various components is starting the Docker containers manually as described here.
To keep commands as concise as possible, only the most basic options are provided. You might want to set additional
ones, e.g., container names or restart policies.

#### Blockchain Node

The blockchain image is a standard Parity client but with a custom configuration for the Trustlines Blockchain. It also
accepts a few additional command line options as described in the help message:

```
$ docker run trustlines/tlbc-testnet --help


 NAME
   Parity Wrapper

 SYNOPSIS
   parity_wrapper.sh [-r] [role] [-a] [address] [-p] [arguments]

 ...
```

Before starting the node, create a Docker network to conveniently allow other containers to connect to it:

```sh
$ docker network create network-laika
```

When running the node, you typically want to forward necessary ports to the host so that Parity can find and connect to
peers. Additionally, you might want to mount some volumes to persist configuration and chain data. For instance, to run
a non-validator node:

```sh
$ mkdir -p trustlines/data-laika trustlines/config trustlines/enode trustlines/shared
$ docker run -d --name laika-node --network network-laika \
    -v $(pwd)/trustlines/data-laika:/data \
    -v $(pwd)/trustlines/config:/config/custom \
    -v $(pwd)/trustlines/enode:/config/network \
    -v $(pwd)/trustlines/shared:/shared/ \
    -p 30300:30300 -p 30300:30300/udp \
    trustlines/tlbc-testnet
```

If you are a validator, this sequence of commands will supply Parity with your keystore file, password, and address so
that it can produce blocks:

```sh
$ mkdir -p trustlines/data-laika trustlines/config/keys/Trustlines trustlines/enode trustlines/shared
$ cp /path/to/your/keystore/file.json trustlines/config/keys/Trustlines
$ echo "<passphrase_for_keystore_file>" > trustlines/config/pass.pwd
$ docker run -d --name laika-node --network network-laika \
    -v $(pwd)/trustlines/data-laika:/data \
    -v $(pwd)/trustlines/config:/config/custom \
    -v $(pwd)/trustlines/enode:/config/network \
    -v $(pwd)/trustlines/shared:/shared/ \
    -p 30300:30300 -p 30300:30300/udp \
    trustlines/tlbc-testnet
```

#### Netstats Client

The netstats client reports the state of your node to the
[Laika netstats page](https://laikanetstats.trustlines.foundation/) that gives a rough overview over the current state
of the network. It is a fully optional component which helps the community, at the cost leaks of some leakage of
private information.

To participate, you first need to request credentials managed by the Trustlines Foundation. Please email
`netstats@trustlines.foundation` to do so.

Once you have your credentials, create a file `trustlines/netstats-env` with the following contents:

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
$ docker run -d --name netstats-client --network network-laika \
    --env-file trustlines/netstats-env \
    -e RPC_HOST=laika-node \
    -e RPC_PORT=8545 \
    trustlines/netstats-client:master
```

#### Monitor

The monitor watches the blockchain and makes sure that validators are online and do not equivocate. Every node in the
network should run it and users should regularly check for reports of misbehaving validators.

Assuming the blockchain node was configured as described above, this command will start the monitor:

```sh
$ mkdir -p trustlines/monitor/reports trustlines/monitor/state
$ docker run -d --name tlbc-monitor --network network-laika \
    -v $(pwd)/trustlines/shared:/config \
    -v $(pwd)/trustlines/monitor/state:/state \
    -v $(pwd)/trustlines/monitor/reports:/reports \
    trustlines/tlbc-monitor \
    -c /config/trustlines-spec.json -r /reports -d /state \
    -u http://laika-node:8545
```

#### Bridge

Validators of the Trustlines Blockchain have to run the bridge that converts TLN tokens on the Ethereum chain to TLC
tokens on the Trustlines Blockchain. Non-validators should not run a bridge node.

The bridge requires an Ethereum mainnet node which can be a light client. To start one, execute

```sh
$ docker network create network-ethereum
$ mkdir -p trustlines/data-goerli
$ docker run -d --name goerli-node --network network-ethereum \
    -v $(pwd)/trustlines/data-goerli:/data \
    -p 30303:30303 -p 30303:30303/udp \
    --user root \
    parity/parity:stable \
    --light --no-download --auto-update none --chain goerli \
    --db-path /data --base-path /data \
    --no-hardware-wallets --jsonrpc-apis safe --jsonrpc-hosts all --jsonrpc-cors all --jsonrpc-port 8545 \
    --no-ipc --no-secretstore --no-color
```

Now, write a configuration file for the bridge node and store it in `trustlines/bridge-config.toml`:

```
[foreign_chain]
rpc_url = "http://goerli-node:8545"
token_contract_address = "0x54B06531214AD41DE9d771c10C0030d048d0cC67"
bridge_contract_address = "0x2171Dd4d4F6ca30FeEA8a27b96257A67f371d87A"
event_fetch_start_block_number = 1321331

[home_chain]
rpc_url = "http://laika-node:8545"
bridge_contract_address = "0x854dF872BB8bfECafFB1077FCfd7aa0B7C838A60"
event_fetch_start_block_number = 4153205

[validator_private_key]
keystore_path = "/config/keys/Trustlines/<keystore_filename.json>"
keystore_password_path = "/config/pass.pwd"
```

Note that they keystore path is not an actual path on the host machine, but rather in the bridge container we will
create next. The container will have to connect to both of the Docker networks and access the config directory.
Therefore, the command looks like this:

```sh
$ docker run -d --name bridge-client --network network-laika --network network-ethereum \
    -v $(pwd)/trustlines/config:/config \
    -v $(pwd)/trustlines/bridge-config.toml:/config/bridge-config.toml \
    trustlines/bridge-next:master \
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
$ docker build -f docker/Dockerfile -t MY_TAGNAME .
$ docker run ... MY_TAGNAME ...
```

### Upload Image

The built image is public available at [DockerHub](https://hub.docker.com/). To upload a new version make sure to have access to the
_trustlines_ organization. If permissions are given, the local build has to be tagged and then pushed.
Please replace `USERNAME` with your own account name on _DockerHub_ and `LOCAL_IMAGE` with the tag name you have given the image while building.
The example below uses the `:latest` tag postfix which is the default one used by _DockerHub_ when pulling an image. If you want to provide an
additional tag (e.g. for sub-versions), adjust the name when tagging.

```sh
$ echo "yoursecretpassword" | docker login --username USERNAME --password-stdin
$ docker tag LOCAL_IMAGE trustlines/tlbc-testnet:latest
$ docker push trustlines/tlbc-testnet:latest
```

### Running Tests on Contracts

First, download and install the solidity compiler solc into bin for compiling the
contracts. You can follow the [official installation documentation](https://solidity.readthedocs.io/en/v0.4.24/installing-solidity.html) or type the following recommand command:

`curl -L -o $HOME/bin/solc https://github.com/ethereum/solidity/releases/download/v0.5.8/solc-static-linux && chmod +x $HOME/bin/solc`

To start developing, you should change directory to the contracts directory `cd contracts`.
Then, install the development dependencies into a venv
with `pip install -c constraints.txt -r requirements.txt`

You can run then run the tests with `pytest tests/`.
To check for linter errors in the contract code you can run `solium --dir contracts/`.
To check for linter errors in the python code you can run `flake8 tests/`.
