# Deploy-Tools

The deploy tools can be used to deploy contracts and interact with them.
The contracts can be found in [blockchain/contracts](https://github.com/trustlines-protocol/blockchain/tree/master/contracts).

## Installation

The installation of any deploy tool will require python 3.6 or up and pip.

You can install the deploy tool you'd like by running `make install` from the desired tool directory.
You can also install any of them by running `make install-deploy-tools/auction-deploy`,
`make install-deploy-tools/bridge-deploy`, or `make install-deploy-tools/validator-set-deploy`, from the root directory.
This will create a virtual Python environment if one was not created yet, install the
dependencies and compile the contracts.
You will then need to activate the created virtual environment with
for example `source venv/bin/activate` from the root directory.

You can then run `auction-deploy --help`, `bridge-deploy --help`, or `validator-set-deploy --help`
to see the available commands for the tool.

## Auction-Deploy commands

The help for `auction-deploy` should detail the following commands if correctly installed:

```bash
Usage: auction-deploy [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  check-whitelist  Check number of not yet whitelisted addresses for the
                   auction

  close            Close the auction at corresponding address.
  deploy           Deploys validator auction, deposit locker, and slasher
                   contract. Initializes the contracts.

  deposit-bids     Move the bids from the auction contract to the deposit
                   locker.

  start            Start the auction at corresponding address.
  status           Prints the values of variables necessary to monitor the
                   auction.

  whitelist        Whitelists addresses for the auction
```

You can also run `auction-deploy <command> --help` to have additional information about a particular command.

## Bridge-Deploy commands

The help for `bridge-deploy` should detail the following commands if correctly installed:

```bash
Usage: bridge-deploy [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  deploy-foreign  Deploys the token bridge on the foreign network and
                  initializes all contracts.

  deploy-home     Deploys the token bridge on the home network.
```

You can also run `bridge-deploy <command> --help` to have additional information about a particular command.

## Validator-Set-Deploy commands

The help for `validator-set-deploy` should detail the following commands if correctly installed:

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

You can also run `validator-set-deploy <command> --help` to have additional information about a particular command.

## Running the tests

You can run the tests on the any tool by running `make test` from the tool directory.
