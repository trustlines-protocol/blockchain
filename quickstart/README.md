# Quickstart

This is the quickstart setup tool for the Trustlines Blockchain and the Laika test network.
It allows an easy and interactive setup of all relevant components.

Please take a look into the main [README](../README.md) to have an overview of the different components it sets up.
It also includes instructions how to easily fetch the most recent version.

## Installation

You can install the quickstart tool by running `make install` from within this directory
or `make install-quickstart` from the root directory.
You will then need to activate the created virtual environment with
for example `source venv/bin/activate` from the root directory.

You can then run `quickstart --help` to confirm the proper installation and see the help.

## Commands

You can run `quickstart laika`, or `quickstart tlbc` to start the interactive script for
the Laika testchain or for the Trustlines blockchain.
You can add the `--expose-ports` option to expose the HTTP and WebSocket ports of the home
node to the local machine on 8545 and 8546 respectively. This is useful if you want to use
the RPC endpoint of the node.

If you want to remap these ports after running the quickstart script, you can modify the file
`tlbc/docker-compose.override.yaml` or `trustlines/docker-compose.override.yaml`
The syntax is `host_port:container_port`, you should only modify the `host_port` value.

Run `quickstart tlbc --help` or `quickstart laika --help` for additional options.
