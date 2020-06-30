# Bridge-Deploy

This tool can be used to deploy bridge related contracts.
The contracts can be found in [blockchain/contracts](https://github.com/trustlines-protocol/blockchain/tree/master/contracts).

## Installation

The installation of the bridge-deploy tool will require python 3.6 or up and pip.

You can install the bridge-deploy tool by running `make install-tools/bridge-deploy` from the root directory.
This will create a virtual Python environment if one was not created yet, install the
dependencies and compile the contracts.
You will then need to activate the created virtual environment with for example `source venv/bin/activate`.

You can then run `bridge-deploy --help` to see the available commands for the tool:

```bash
Usage: bridge-deploy [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  deploy-foreign  Deploys the token bridge on the foreign network and
                  initializes all contracts.

  deploy-home     Deploys the token bridge on the home network.
```

## Running the tests

You can run the tests on the bridge-deploy tool by running `make test-tools/bridge-deploy` from the root directory.
