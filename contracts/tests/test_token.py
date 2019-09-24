import eth_tester.exceptions
import pytest


@pytest.fixture()
def tln_token_contract_with_allowance(
    tln_token_contract, allowed_spender, allowance, premint_token_address
):

    tln_token_contract.functions.approve(allowed_spender, allowance).transact(
        {"from": premint_token_address}
    )
    assert (
        tln_token_contract.functions.allowance(
            premint_token_address, allowed_spender
        ).call()
        == allowance
    )

    return tln_token_contract


@pytest.fixture(scope="session")
def allowed_spender(accounts):
    return accounts[1]


@pytest.fixture(scope="session")
def allowance():
    return 12345


def test_premint(tln_token_contract, premint_token_address, premint_token_value):
    assert tln_token_contract.functions.totalSupply().call() == premint_token_value
    assert (
        tln_token_contract.functions.balanceOf(premint_token_address).call()
        == premint_token_value
    )


def test_race_condition_fix_on_allowance(
    tln_token_contract_with_allowance,
    chain,
    accounts,
    premint_token_address,
    allowed_spender,
    allowance,
):
    allower = premint_token_address
    spender = allowed_spender
    receiver = accounts[3]

    chain.disable_auto_mine_transactions()

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        tln_token_contract_with_allowance.functions.transferFrom(
            allower, receiver, allowance
        ).transact({"from": spender})
        tln_token_contract_with_allowance.functions.approve(
            spender, allowance
        ).transact({"from": allower})
    chain.enable_auto_mine_transactions()


def test_unlimited_allowance(tln_token_contract, premint_token_address, accounts):
    max_uint = 2 ** 256 - 1
    spender = accounts[1]
    receiver = accounts[2]
    spending = 456

    tln_token_contract.functions.approve(spender, max_uint).transact(
        {"from": premint_token_address}
    )
    tln_token_contract.functions.transferFrom(
        premint_token_address, receiver, spending
    ).transact({"from": spender})

    assert (
        tln_token_contract.functions.allowance(premint_token_address, spender).call()
        == max_uint
    )


def test_burning(tln_token_contract, premint_token_address, premint_token_value):
    burn_amount = 654
    tln_token_contract.functions.burn(burn_amount).transact(
        {"from": premint_token_address}
    )

    assert (
        tln_token_contract.functions.balanceOf(premint_token_address).call()
        == premint_token_value - burn_amount
    )
    assert (
        tln_token_contract.functions.totalSupply().call()
        == premint_token_value - burn_amount
    )


def test_transfer(
    tln_token_contract, premint_token_address, premint_token_value, accounts
):
    transfer_amount = 789
    receiver = accounts[2]
    tln_token_contract.functions.transfer(receiver, transfer_amount).transact(
        {"from": premint_token_address}
    )

    assert (
        tln_token_contract.functions.balanceOf(premint_token_address).call()
        == premint_token_value - transfer_amount
    )
    assert tln_token_contract.functions.balanceOf(receiver).call() == transfer_amount


def test_approve(tln_token_contract, accounts):
    approver = accounts[2]
    receiver = accounts[3]
    allowance = 852

    tln_token_contract.functions.approve(receiver, allowance).transact(
        {"from": approver}
    )

    assert (
        tln_token_contract.functions.allowance(approver, receiver).call() == allowance
    )


def test_transfer_from(
    tln_token_contract_with_allowance,
    premint_token_address,
    premint_token_value,
    allowed_spender,
    allowance,
    accounts,
):
    receiver = accounts[5]
    transfer_amount = 456

    tln_token_contract_with_allowance.functions.transferFrom(
        premint_token_address, receiver, transfer_amount
    ).transact({"from": allowed_spender})

    assert (
        tln_token_contract_with_allowance.functions.balanceOf(
            premint_token_address
        ).call()
        == premint_token_value - transfer_amount
    )
    assert (
        tln_token_contract_with_allowance.functions.balanceOf(receiver).call()
        == transfer_amount
    )
    assert (
        tln_token_contract_with_allowance.functions.balanceOf(allowed_spender).call()
        == 0
    )
    assert (
        tln_token_contract_with_allowance.functions.allowance(
            premint_token_address, allowed_spender
        ).call()
        == allowance - transfer_amount
    )
