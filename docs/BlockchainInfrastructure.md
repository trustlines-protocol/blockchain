## The Trustlines Blockchain Infrastructure

This document describes the trustlines blockchain infrastructure
which involves multiple components across this repository.

Nodes of the Trustlines Blockchain run various applications:

- The node of the blockchain itself
- The monitor that checks if validators act honestly (optional)
- The bridge between Ethereum mainnet and the Trustlines Blockchain (only run by validators)
- The netstats client to report the node state to `https://netstats.tlbc.trustlines.foundation` (optional)

There are multiple ways to set each of these up.
The most straightforward one by far is via our interactive quickstartscript.
Finer control can be achieved by starting the components individually as Docker containers.
Finally, it is also possible to avoid Docker altogether and run everything directly on the host machine.

Before starting the installation process, please have a look at the following
sections on the distinction between Laika and the Trustlines Blockchain, system
requirements, and security.

### TLBC and Laika

There are two different blockchains related to this project. The first one is
a testnet called Laika. The second one is considered to be the mainnet for Trustlines and
called the Trustlines Blockchain or TLBC. The instructions within this document
primarily focus on the Trustlines Blockchain.

### System Requirements

Based on the experiences we have had on our long-running testnet Laika,
we recommend to run a Laika or tlbc node on a machine with at least 4GB of memory and 20GB of SSD storage.

Validators should make sure their node has a high uptime. Otherwise, they miss out on potential revenue and harm the
network by increasing average block intervals and time to finality.

For block validation and creation, it is essential to make sure your host system has the correct time configuration.
On most systems, this should be the case by default. You can check the settings with `timedatectl` (look for
`"System clock synchronized: yes"`). For more information, see for example the corresponding
[Ubuntu help page](https://help.ubuntu.com/lts/serverguide/NTP.html).

For the Docker installation modes, [Docker](https://docker.com) needs to be installed and configured.
For the quickstart mode, [docker-compose](https://docs.docker.com/compose/) needs to be installed as well.
You must have at least version [`1.18.0`](https://github.com/docker/compose/releases/tag/1.18.0) of `docker-compose`.
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

To fetch and run the most recent version of the quickstart script for the Trustlines Blockchain,
execute the following command on your machine:

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
`tlbc` directory placed in the current working directory (`trustlines` in case of a Laika setup).
It is possible to customize the own setup by editing those configuration files. This goes
for the configuration of the different components, as well as the composition of the
Docker containers. If an optional component has not been set up on an earlier
run, it can be added later by executing the quickstart script again.

Executing the script again is safe: No configuration will be overridden without
asking, in case the user has changed them itself. If conflicting configuration
updates occur, they are shown to the user who can ask to see a diff of the
changes.

### Setup with Docker

A more explicit way of setting up the various components is starting the Docker containers manually as described
in the [docker setup documentation](https://github.com/trustlines-protocol/blockchain/tree/master/docs/DockerSetup.md).

### Setup Without Docker

We refer to the documentation of the individual components:

- [Parity](https://wiki.parity.io/Parity-Ethereum)
- [Netstats](https://github.com/trustlines-protocol/ethstats-client)
- [Monitor](https://github.com/trustlines-protocol/tlbc-monitor)
- [Bridge](https://github.com/trustlines-protocol/blockchain/tree/master/bridge)

For the Trustlines Blockchain node, make sure it uses the correct chain
specification file (`./chain/tlbc/tlbc-spec.json`), that the right TCP and UDP
ports are used (30302), and that the JSON RPC APIs `web3`, `eth`, and `net` are
enabled.

## access.laika.trustlines.foundation

The Trustlines Foundation hosts a publically accessible node for the
Laika Testnet.

You can access it via the following URL:
https://access.laika.trustlines.foundation
