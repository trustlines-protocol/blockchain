import pytest

from click.testing import CliRunner

from bridge_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_deploy_bridge_validators(runner):

    result = runner.invoke(
        main,
        args=(
            "deploy-validators"
            " --jsonrpc test"
            " --validator-proxy-address 0x0000000000000000000000000000000000000000"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home(
    runner, chain, block_reward_contract, home_bridge_validators_contract
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home"
            " --jsonrpc test "
            f" --bridge-validators-address {home_bridge_validators_contract.address}"
            f" --owner-address {chain.get_accounts()[0]}"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home_custom_block_reward_amount(
    runner, chain, block_reward_contract, home_bridge_validators_contract
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home"
            " --jsonrpc test "
            f" --bridge-validators-address {home_bridge_validators_contract.address}"
            f" --owner-address {chain.get_accounts()[0]}"
            " --block-reward-amount 1"
        ),
    )

    assert result.exit_code == 0


def test_deploy_foreign(runner):

    result = runner.invoke(main, args="deploy-foreign --jsonrpc test")

    assert result.exit_code == 0


def test_print_home(runner):

    result = runner.invoke(main, args="print-home --jsonrpc test")

    assert result.exit_code == 0


def test_print_foreign(runner):

    result = runner.invoke(main, args="print-foreign --jsonrpc test")

    assert result.exit_code == 0
