#! pytest -s

"""This is used to test the gas usage of the home bridge
 contract. This file can be used as a standalone scripts.
"""

import pytest

minimal_number_of_validators = 50
maximal_number_of_validators = 123

# Keep in sync with CONFIRMATION_TRANSACTION_GAS_LIMIT in bridge/constants.py
maximal_allowed_gas_usage = 500_000


@pytest.fixture(params=[maximal_number_of_validators, minimal_number_of_validators])
def number_of_validators(request):
    """the number of validators."""
    return request.param


@pytest.fixture()
def required_confirmations(number_of_validators):
    """the number of confirmations required"""
    return (number_of_validators * 50 + 99) // 100


@pytest.fixture(scope="session")
def all_proxy_validators(chain):
    """list of 123 accounts that can be used as validators"""
    account_0 = chain.get_accounts()[0]
    validators = []
    for i in range(maximal_number_of_validators):
        # use an offset for the account number in order to not
        # generate the same keys we generate in the whitelist fixture
        account_num = 20000000 + i
        new_account = chain.add_account(f"0x{account_num:064}")
        chain.send_transaction(
            {
                "from": account_0,
                "to": new_account,
                "gas": 100000,
                "value": 1_000_000_000,
            }
        )
        validators.append(new_account)

    return validators


@pytest.fixture()
def proxy_validators(all_proxy_validators, number_of_validators):
    """The validators used in the proxy contract. This replaces the
    fixture with the same name from conftest.py"""
    return all_proxy_validators[:number_of_validators]


@pytest.fixture
def confirm_nth(home_bridge_contract, proxy_validators, web3):
    """confirm a transfer by the nth validator"""

    class ConfirmNth:
        transfer_hash = "0x" + b"     transfer-hash              ".hex()
        tx_hash = "0x" + b"     tx-hash                    ".hex()
        amount = 20000
        recipient = "0xFCB047cCD297048b6F31fbb2fef14001FefFa0f3"

        def __call__(self, n, fail_ok=False):
            validator = proxy_validators[n]
            transact_args = {"from": validator}
            if fail_ok:
                # we pass in the gas here in order to not make it not
                # raise while estimating gas
                transact_args["gas"] = 2_000_000

            tx_hash = home_bridge_contract.functions.confirmTransfer(
                transferHash=self.transfer_hash,
                transactionHash=self.tx_hash,
                amount=self.amount,
                recipient=self.recipient,
            ).transact(transact_args)
            tx_receipt = web3.eth.getTransactionReceipt(tx_hash)
            gas = tx_receipt.gasUsed
            print(
                f"validator {n+1} {validator} confirmed, gas: {gas}, status: {tx_receipt.status}"
            )
            return gas

    return ConfirmNth()


def test_gas_cost_complete_transfer(
    home_bridge_contract,
    proxy_validators,
    confirm_nth,
    web3,
    number_of_validators,
    required_confirmations,
):
    """This walks through a complete Transfer on the home bridge and
    checks gas usage limits
    """
    print(
        f"\n=====> {number_of_validators} validators, {required_confirmations} confirmations required"
    )
    get_transfer_completed_events = home_bridge_contract.events.TransferCompleted.createFilter(
        fromBlock=web3.eth.blockNumber
    ).get_all_entries

    for i in range(required_confirmations - 1):
        gas = confirm_nth(i)
        assert gas < 120_000 < maximal_allowed_gas_usage

    assert not get_transfer_completed_events()

    # complete the transfer
    print("Completing the transfer")
    gas = confirm_nth(required_confirmations - 1)
    assert gas < maximal_allowed_gas_usage
    assert get_transfer_completed_events()

    print("Confirm after complete")
    gas = confirm_nth(required_confirmations, fail_ok=True)
    assert gas < 50000 < maximal_allowed_gas_usage
    print("")


def test_gas_cost_complete_transfer_with_validator_set_changed(
    home_bridge_contract,
    proxy_validators,
    confirm_nth,
    web3,
    number_of_validators,
    required_confirmations,
    system_address,
    validator_proxy_with_validators,
):
    """This walks through a complete Transfer on the home bridge and
    checks gas usage limits
    """
    print(
        f"\n=====> validator set will change, {number_of_validators} validators, {required_confirmations} confirmations required"
    )
    get_transfer_completed_events = home_bridge_contract.events.TransferCompleted.createFilter(
        fromBlock=web3.eth.blockNumber
    ).get_all_entries

    for i in range(required_confirmations - 1):
        gas = confirm_nth(i)
        assert gas < 120_000 < maximal_allowed_gas_usage

    assert not get_transfer_completed_events()

    # changing the validator set
    print("Changing the validator set")
    validator_proxy_with_validators.functions.updateValidators(
        proxy_validators[required_confirmations - 1 : required_confirmations]
    ).transact({"from": system_address})

    # complete the transfer
    print("Completing the transfer")
    gas = confirm_nth(required_confirmations - 1)
    assert gas < maximal_allowed_gas_usage
    assert get_transfer_completed_events()
