from bridge_deploy.core import deploy_foreign_bridge_contract


def test_deploy_foreign_bridge_contract(web3):
    foreign_bridge_contract = deploy_foreign_bridge_contract(
        token_contract_address="0x5757957701948584cc2A8293857D89b19De44f0F", web3=web3
    )

    assert (
        foreign_bridge_contract.address != "0x0000000000000000000000000000000000000000"
    )
