import pytest
from eth_tester.exceptions import TransactionFailed


@pytest.fixture()
def foreign_bridge_with_token_balance(
    foreign_bridge_contract, tln_token_contract, premint_token_address
):
    transfer_amount = 1

    tln_token_contract.functions.transfer(
        foreign_bridge_contract.address, transfer_amount
    ).transact({"from": premint_token_address})

    assert (
        tln_token_contract.functions.balanceOf(foreign_bridge_contract.address).call()
        == transfer_amount
    )

    return foreign_bridge_contract


def test_burn_token(foreign_bridge_with_token_balance, tln_token_contract):
    assert (
        tln_token_contract.functions.balanceOf(
            foreign_bridge_with_token_balance.address
        ).call()
        > 0
    )

    foreign_bridge_with_token_balance.functions.burn().transact()

    assert (
        tln_token_contract.functions.balanceOf(
            foreign_bridge_with_token_balance.address
        ).call()
        == 0
    )


def test_burn_token_with_zero_balance(foreign_bridge_with_token_balance):
    foreign_bridge_with_token_balance.functions.burn().transact()
    foreign_bridge_with_token_balance.functions.burn().transact()


def test_deploy_with_zero_token_address_fails(deploy_contract):
    with pytest.raises(TransactionFailed):
        deploy_contract(
            "ForeignBridge",
            constructor_args=("0x0000000000000000000000000000000000000000",),
        )
