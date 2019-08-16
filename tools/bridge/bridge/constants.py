HOME_CHAIN_STEP_DURATION = 5

TRANSFER_EVENT_NAME = "Transfer"
CONFIRMATION_EVENT_NAME = "Confirmation"
COMPLETION_EVENT_NAME = "TransferCompleted"

# Gas limit used for confirmation transactions. The actual gas usage can be determined with
# test_measure_gas_home_bridge.py found in the smart contract test directory. As of commit
# cc46ea961ece850ce28a2d62b7c484f8fa82ca3c, this is 321004, but we add a generous safety margin.
# On changing this value, update the corresponding constant in the test script accordingly.
CONFIRMATION_TRANSACTION_GAS_LIMIT = 400_000

# maximum amount of time in seconds application greenlets have to cleanup before shutdown
APPLICATION_CLEANUP_TIMEOUT = 5
