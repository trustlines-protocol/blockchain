from bridge_deploy.foreign import deploy_foreign_bridge_contract


def test_deploy_foreign_bridge_contract(web3):
    foreign_bridge_contract = deploy_foreign_bridge_contract(web3=web3)

    assert (
        foreign_bridge_contract.address != "0x0000000000000000000000000000000000000000"
    )
