# Trustlines Blockchain

The Trustlines Blockchain is a component of the [Trustlines Protocol](https://trustlines.foundation/protocol.html).
The Trustlines Protocol is a set of rules to allow the transfer of value on top of existing trust
relationships stored on a trustless infrastructure, here a blockchain.

This repository is a mono-repository containing multiple different packages related to the Trustlines Blockchain (tlbc)
considered as the mainnet for Trustlines, and to Laika, considered as the testnet for Trustlines.

It contains:
- blockchain client configurations and dockerfiles for tlbc and laika, found in `./chain/`
- contracts implementation of the Trustlines auction, the bridge, the validator set, and the Trustlines Network Token
found in `./contracts/`
- python packages for deploying these contracts via cli found in the `./deploy-tools/` folder:
`auction-deploy`, `bridge-deploy`, and `validator-set-deploy`
- the bridge client ran by bridge validators found in `./bridge/`
- the quickstart package used to easily set up a tlbc or Laika node found in `./quickstart/`

## Read more

To learn more about the Trustlines Blockchain infrastructure or how to run a blockchain node,
refer to the [Trustlines Blockchain documentation](docs/BlockchainInfrastructure.md)

You can also learn more about
[the contracts](contracts/README.md),
[the auction-deploy tool](deploy-tools/auction-deploy/README.md),
[the bridge](bridge/README.md),
[the bridge-deploy tool](deploy-tools/bridge-deploy/README.md),
[the quickstart](quickstart/README.md),
[the validator-set-deploy tool](deploy-tools/validator-set-deploy/README.md),
by reading their corresponding readmes.

## Installation

An installation of all the components of this repository will require python 3.6 or up and pip.

This repository contains a `Makefile` at its root and multiple different `Makefiles`
in each component's directory. You can install all the components in one command
by running `make install` from the root directory.
