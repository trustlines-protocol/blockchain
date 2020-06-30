# Auction-Deploy

This tool can be used to deploy auction related contracts.
The contracts can be found in [blockchain/contracts](https://github.com/trustlines-protocol/blockchain/tree/master/contracts).

## Installation

The installation of the auction-deploy tool will require python 3.6 or up and pip.

You can install the auction-deploy tool by running `make install-tools/auction-deploy` from the root directory.
This will create a virtual Python environment if one was not created yet, install the
dependencies and compile the contracts.
You will then need to activate the created virtual environment with for example `source venv/bin/activate`.

You can then run `auction-deploy --help` to see the available commands for the tool:

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

## Running the tests

You can run the tests on the auction-deploy tool by running `make test-tools/auction-deploy` from the root directory.
