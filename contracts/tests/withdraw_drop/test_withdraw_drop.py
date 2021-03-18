import eth_tester.exceptions
import pytest


@pytest.fixture(scope="session")
def withdraw_drop_contract(
    deploy_contract,
    tln_token_contract,
    airdrop_list,
    airdrop_values,
    owner,
    airdrop_time_limit,
    web3,
    premint_token_address,
):
    contract = deploy_contract(
        "WithdrawDrop",
        constructor_args=(
            airdrop_list,
            airdrop_values,
            tln_token_contract.address,
            owner,
            airdrop_time_limit,
        ),
    )

    total_dropped_value = 0
    for value in airdrop_values:
        total_dropped_value += value
    tln_token_contract.functions.transfer(
        contract.address, total_dropped_value
    ).transact({"from": premint_token_address})

    return contract


@pytest.fixture(scope="session")
def airdrop_list(whitelist):
    return [whitelist[i] for i in range(70)]


@pytest.fixture(scope="session")
def airdrop_values():
    # we do not want to have a zero value
    return [i for i in range(1, 71)]


@pytest.fixture(scope="session")
def owner(accounts):
    return accounts[0]


@pytest.fixture(scope="session")
def airdrop_time_limit():
    return 5_000_000_000


def test_constructor_values(
    withdraw_drop_contract,
    airdrop_list,
    airdrop_values,
    tln_token_contract,
    owner,
    airdrop_time_limit,
):
    for (recipient, value) in zip(airdrop_list, airdrop_values):
        assert withdraw_drop_contract.functions.allowances(recipient).call() == value

    assert (
        withdraw_drop_contract.functions.droppedToken().call()
        == tln_token_contract.address
    )
    assert withdraw_drop_contract.functions.owner().call() == owner
    assert withdraw_drop_contract.functions.timeLimit().call() == airdrop_time_limit


def test_withdraws(
    withdraw_drop_contract, airdrop_list, airdrop_values, tln_token_contract
):
    for (recipient, value) in zip(airdrop_list, airdrop_values):
        recipient_pre_balance = tln_token_contract.functions.balanceOf(recipient).call()
        airdrop_pre_balance = tln_token_contract.functions.balanceOf(
            withdraw_drop_contract.address
        ).call()

        withdraw_drop_contract.functions.withdraw().transact({"from": recipient})

        recipient_post_balance = tln_token_contract.functions.balanceOf(
            recipient
        ).call()
        airdrop_post_balance = tln_token_contract.functions.balanceOf(
            withdraw_drop_contract.address
        ).call()

        assert recipient_post_balance - recipient_pre_balance == value
        assert airdrop_pre_balance - airdrop_post_balance == value
    assert (
        tln_token_contract.functions.balanceOf(withdraw_drop_contract.address).call()
        == 0
    )


def test_withdraw_twice(withdraw_drop_contract, airdrop_list):
    recipient = airdrop_list[0]
    withdraw_drop_contract.functions.withdraw().transact({"from": recipient})
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        withdraw_drop_contract.functions.withdraw().transact({"from": recipient})


def test_withdraw_not_listed(withdraw_drop_contract, accounts, airdrop_list):
    not_whitelisted = accounts[0]
    assert (
        not_whitelisted not in airdrop_list
    ), "Test cannot be conducted as `not_whitelisted` is actually whitelisted"

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        withdraw_drop_contract.functions.withdraw().transact({"from": not_whitelisted})


def test_close_aidrop(
    withdraw_drop_contract,
    tln_token_contract,
    owner,
    accounts,
    chain,
    airdrop_time_limit,
):
    not_owner = accounts[1]
    assert (
        not_owner != owner
    ), "Test cannot be conducted as `not_owner` is actually owner"

    chain.time_travel(airdrop_time_limit)
    chain.mine_block()

    owner_pre_balance = tln_token_contract.functions.balanceOf(owner).call()
    airdrop_pre_balance = tln_token_contract.functions.balanceOf(
        withdraw_drop_contract.address
    ).call()

    withdraw_drop_contract.functions.closeDrop().transact({"from": not_owner})

    owner_post_balance = tln_token_contract.functions.balanceOf(owner).call()
    airdrop_post_balance = tln_token_contract.functions.balanceOf(
        withdraw_drop_contract.address
    ).call()

    assert owner_post_balance - owner_pre_balance == airdrop_pre_balance
    assert airdrop_post_balance == 0


def test_close_aidrop_too_soon(withdraw_drop_contract, owner):
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        withdraw_drop_contract.functions.closeDrop().transact({"from": owner})


def test_withdraw_after_closed_aidrop(
    withdraw_drop_contract,
    tln_token_contract,
    owner,
    chain,
    airdrop_time_limit,
    airdrop_list,
):
    chain.time_travel(airdrop_time_limit)
    chain.mine_block()
    withdraw_drop_contract.functions.closeDrop().transact({"from": owner})

    recipient = airdrop_list[0]
    recipient_pre_balance = tln_token_contract.functions.balanceOf(recipient).call()
    withdraw_drop_contract.functions.withdraw().transact({"from": airdrop_list[0]})
    recipient_post_balance = tln_token_contract.functions.balanceOf(recipient).call()

    assert recipient_pre_balance == recipient_post_balance
