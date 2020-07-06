
<a href="https://github.com/psf/black"><img alt="Black" src="https://img.shields.io/badge/code%20style-black-000000.svg"></a>
<a href="https://circleci.com/gh/trustlines-protocol/blockchain"><img alt="CircleCi" src="https://circleci.com/gh/trustlines-protocol/blockchain.svg?style=svg"></a>
<a href="https://gitter.im/trustlines/community"><img alt="Black" src="https://badges.gitter.im/Join%20Chat.svg"></a>

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

## Get Up and Running

To quickly get a tlbc or Laika node running, we advise you to use the quickstart script.
It will guide you through the step of setting up a node and optional components such as the bridge,
a chain monitor, and a netstats client.

You will need to have [Docker](https://docker.com) and [docker-compose](https://docs.docker.com/compose/)
installed and configured. You must have at least version [`1.18.0`](https://github.com/docker/compose/releases/tag/1.18.0)
of `docker-compose`. Please refer to the official documentation and make sure your user is added
 to the `docker` user group if you cannot access root permissions to run containers.

To fetch and run the most recent version of the quickstart script for tlbc,
execute the following command on your machine:

```sh
bash <(curl -L quickstart.tlbc.trustlines.foundation)
```

If you want a quickstart setup for the Laika testnet, use the following command instead:

```sh
bash <(curl -L quickstart.laika.trustlines.foundation)
```

## Public Laika Node

The Trustlines Foundation hosts a publically accessible node for the
Laika Testnet.

You can access it via the following URL:
https://access.laika.trustlines.foundation

## Start Developing

We refer you to the different readmes of the components you want to start developing on.

You can however install all the components of this repository if you have python 3.6 or up and pip by
using the command `make install`. This will create a virtual environment and install the requirements
as well as each components. You will need to activate the virtual environment with for example
`source venv/bin/activate` from the root directory.

## Contributing

Contributions are highly appreciated, but please check our `contributing guidelines </CONTRIBUTING.md>`__.

### Pre-commit hooks

You should consider initializing the pre-commit hooks. The
installed git pre-commit hooks run flake8 and black among other things
when committing changes to the git repository.
Install them with `pre-commit install`. You can run them on all files with `pre-commit run -a`.

## Changlogs

We only keep a changelog for each chain, [tlbc](/chain/tlbc/CHANGELOG.rst),
and [Laika](/chain/laika/CHANGELOG.rst) as well as for the [bridge](/bridge/CHANGELOG.rst).

## Read more

To learn more about the Trustlines Blockchain infrastructure or how to run a blockchain node,
refer to the [Trustlines Blockchain documentation](docs/BlockchainInfrastructure.md)

You can also learn more about
[the contracts](contracts/README.md),
[the quickstart](quickstart/README.md),
[the bridge](bridge/README.md),
[the auction-deploy tool](deploy-tools/README.md),
[the bridge-deploy tool](deploy-tools/README.md),
[the validator-set-deploy tool](deploy-tools/README.md),
by reading their corresponding readmes.

## Installation

An installation of all the components of this repository will require python 3.6 or up and pip.

This repository contains a `Makefile` at its root and multiple different `Makefiles`
in each component's directory. You can install all the components in one command
by running `make install` from the root directory.
