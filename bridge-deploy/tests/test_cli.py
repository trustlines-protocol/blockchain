import pytest

from click.testing import CliRunner

from bridge_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_deploy_reward(runner):

    result = runner.invoke(main, args="deploy-reward --jsonrpc test")

    assert result.exit_code == 0


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


# def test_deploy_home(runner, home_bridge_contract, home_bridge_validators_contract):
#
#     result = runner.invoke(
#         main,
#         args=(
#             "deploy-home"
#             " --jsonrpc test "
#             f" --validator-set-address {home_bridge_contract.address}"
#             f" --block-reward-address {home_bridge_validators_contract.address}"
#         ),
#     )
#
#     assert result.exit_code == 0


def test_deploy_foreign(runner):

    result = runner.invoke(main, args="deploy-foreign --jsonrpc test")

    assert result.exit_code == 0


def test_print_home(runner):

    result = runner.invoke(main, args="print-home --jsonrpc test")

    assert result.exit_code == 0


def test_print_foreign(runner):

    result = runner.invoke(main, args="print-foreign --jsonrpc test")

    assert result.exit_code == 0
