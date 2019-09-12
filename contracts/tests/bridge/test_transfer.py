import pytest


@pytest.fixture()
def test_recipient_contract(deploy_contract):
    return deploy_contract("TestRecipient", constructor_args=())


@pytest.fixture()
def recipient(test_recipient_contract):
    return test_recipient_contract.address


@pytest.fixture()
def test_transfer_contract(deploy_contract, web3, accounts):

    contract = deploy_contract("TestTransfer", constructor_args=())

    account_0 = accounts[0]

    web3.eth.sendTransaction(
        {
            "from": account_0,
            "to": contract.address,
            "gas": 100_000,
            "value": 5 * 10 ** 18,
        }
    )

    return contract


@pytest.mark.parametrize("gas", [35000, 40000, 50000, 100000])
def test_transfer(
    test_transfer_contract, accounts, web3, recipient, gas, test_recipient_contract
):

    get_events = test_recipient_contract.events.GasLeft.createFilter(
        fromBlock=web3.eth.blockNumber
    ).get_all_entries

    tx_hash = test_transfer_contract.functions.doit(recipient).transact({"gas": gas})
    tx_receipt = web3.eth.getTransactionReceipt(tx_hash)

    balance = web3.eth.getBalance(recipient)

    print(
        f"\n\ngas: {gas} status: {tx_receipt.status} gas used: {tx_receipt.gasUsed} balance: {balance}"
    )
    print(get_events())

    # print(tx_receipt)

    if tx_receipt.status == 1:
        assert balance == 1

    # assert (
    #     tx_receipt.status != 1 or balance == 1
    # ), "tx succeded but internal transfer failed"
