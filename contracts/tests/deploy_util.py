from deploy_tools.deploy import wait_for_successful_transaction_receipt


def initialize_validator_set(test_validator_set_contract, validators, web3):
    txid = test_validator_set_contract.functions.init(validators).transact(
        {"from": web3.eth.defaultAccount}
    )
    wait_for_successful_transaction_receipt(web3, txid)
    return test_validator_set_contract


def initialize_test_validator_slasher(deployed_contract, fund_contract_address, web3):
    txid = deployed_contract.functions.init(fund_contract_address).transact(
        {"from": web3.eth.defaultAccount}
    )
    wait_for_successful_transaction_receipt(web3, txid)
    return deployed_contract


def initialize_deposit_locker(
    deployed_contract,
    release_timestamp,
    validator_contract_address,
    auction_contract_address,
    web3,
):
    txid = deployed_contract.functions.init(
        _releaseTimestamp=release_timestamp,
        _slasher=validator_contract_address,
        _depositorsProxy=auction_contract_address,
    ).transact({"from": web3.eth.defaultAccount})
    wait_for_successful_transaction_receipt(web3, txid)
    return deployed_contract
