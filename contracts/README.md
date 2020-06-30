# Contracts

This folder contains the contracts for:

- the Trustlines validator auction, both for eth and token based auctions
- the bridge
- the validator set on tlbc
- slashing validators on tlbc and their deposit on the Ethereum mainnet
- the Trustlines Network Token

### Running Tests on Contracts

You will need the solidity compiler `solc` version `0.5.8` for compiling the contracts.
You can follow the [official installation documentation](https://solidity.readthedocs.io/en/v0.5.8/installing-solidity.html).
From the root directory, you can run the tests by calling `make test-contracts`.
This will create a virtual Python environment, install the
dependencies, compile the contracts and run the tests.
