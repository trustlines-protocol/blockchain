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


@pytest.mark.parametrize("gas", [200_000, 50_700, 30_000])
def test_transfer(test_transfer_contract, accounts, web3, recipient, gas):
    tx_hash = test_transfer_contract.functions.doit(recipient).transact({"gas": gas})
    tx_receipt = web3.eth.getTransactionReceipt(tx_hash)

    balance = web3.eth.getBalance(recipient)

    print(
        f"gas: {gas} status: {tx_receipt.status} gas used: {tx_receipt.gasUsed} balance: {balance}"
    )

    assert (
        tx_receipt.status != 1 or balance == 1
    ), "tx succeded but internal transfer failed"
