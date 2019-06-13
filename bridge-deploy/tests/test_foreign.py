from bridge_deploy.foreign import deploy_foreign_bridge_contract


def test_deploy_foreign_bridge_contract(web3):
    block_number = web3.eth.blockNumber
    deployment_result = deploy_foreign_bridge_contract(web3=web3)

    assert deployment_result.foreign_bridge_block_number == block_number
    assert (
        deployment_result.foreign_bridge.address
        != "0x0000000000000000000000000000000000000000"
    )
