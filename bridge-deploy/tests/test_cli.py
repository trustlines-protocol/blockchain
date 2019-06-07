import pytest

from click.testing import CliRunner

from bridge_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_deploy_home(runner):

    # TODO: Add actual working addresses and contracts
    result = runner.invoke(
        main,
        args=(
            "deploy-home"
            " --jsonrpc test "
            " --validator-set-address 0x0000000000000000000000000000000000000002"
            " --block-reward-address 0x0000000000000000000000000000000000000002"
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
