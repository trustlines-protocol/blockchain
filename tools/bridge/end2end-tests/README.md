# Bridge end2end tests

These are the end2tests of the Trustlines Blockchain Bridge (tlbc-bridge).


## Requirements
To run the end2end tests you have to have the tlbc-bridge
installed in your environment. This will be automatically done if using `make`.
Additionally you have to have parity installed.

## Run
To run the end2end tests, use
`make test-end2end`
from the `tools/bridge` directory, or use `make test-end2end-tools/bridge`
from the blockchain root directory.

## Run without make
To run the tests without `make`, make sure that the tlbc-bridge and parity
is installed. Then run `pytest tools/bridge/end2end-tests/tests`.

## Test Structure
The end2end tests start all relevant parts of the bridge in separate processes in the background.
It will check that every service is ready (can be defined for every service separatly) before starting the end2end tests.
A strong emphasis is on making the tests reliable, but also fast. This should be done by not using bare `sleeps`,
but instead poll with a timeout.
