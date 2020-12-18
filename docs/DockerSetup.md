## Setup With Docker

This document describes how to set up a Trustlines Blockchain (tlbc) node running with docker.
It also explains how to run components associated with the tlbc node,
such as the netstats client, the monitor, and the bridge
To keep commands as concise as possible, only the most basic options are provided. You might want to set additional
ones, e.g. container names or restart policies.

Alternatively, you could also use the quickstart script described in the
[readme](https://github.com/trustlines-protocol/blockchain/tree/master/README.md).
and adjust the setup afterwards with commands similar to the
following ones.

### Blockchain Node

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
    -p 30302:3030r -p 30302:30302/udp \
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
    -p 30302:30302 -p 30302:30302/udp \
    trustlines/tlbc-node:release
```

### Netstats Client

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

### Monitor

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

### Bridge

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
