from bridge_deploy.core import (
    deploy_foreign_bridge_contract,
    deploy_home_bridge_contract,
)


def test_deploy_foreign_bridge_contract(web3, abitrary_address):
    foreign_bridge_contract = deploy_foreign_bridge_contract(
        token_contract_address=abitrary_address, web3=web3
    )

    assert (
        foreign_bridge_contract.address != "0x0000000000000000000000000000000000000000"
    )


def test_deploy_home_bridge_contract(web3, abitrary_address):
    home_bridge_contract = deploy_home_bridge_contract(
        validator_proxy_contract_address=abitrary_address,
        validators_required_percent=40,
        web3=web3,
    )

    assert home_bridge_contract.address != "0x0000000000000000000000000000000000000000"
