# Validator-Set-Deploy

This tool can be used to deploy validator set related contracts.
The contracts can be found in [blockchain/contracts](https://github.com/trustlines-protocol/blockchain/tree/master/contracts).

## Installation

The installation of the validator-set-deploy tool will require python 3.6 or up and pip.

You can install the validator-set-deploy tool by running `make install-tools/validator-set-deploy` 
from the root directory. This will create a virtual Python environment if one was not created yet,
install the dependencies and compile the contracts.
You will then need to activate the created virtual environment with for example `source venv/bin/activate`.

You can then run `validator-set-deploy --help` to see the available commands for the tool:

```bash
Usage: validator-set-deploy [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  check-validators  Check that the current validators of the contract are
                    matching the one in the given file.

  deploy            Deploys the validator set and initializes with the
                    validator addresses.

  deploy-proxy      Deploys the validator proxy and initializes with the
                    validator addresses within the given validator csv file.

  print-validators  Prints the current validators.
```

## Running the tests

You can run the tests on the validator-set-deploy tool by running 
`make test-tools/validator-set-deploy` from the root directory.
