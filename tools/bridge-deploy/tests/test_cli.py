import pytest

from click.testing import CliRunner

from bridge_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_deploy_foreign(runner, abitrary_address):
    result = runner.invoke(
        main, args=f"deploy-foreign --jsonrpc test --token-address {abitrary_address}"
    )

    assert result.exit_code == 0


def test_print_foreign(runner):
    result = runner.invoke(main, args=f"print-foreign --jsonrpc test")

    assert result.exit_code == 0


def test_deploy_home(runner, abitrary_address):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home_with_required_percentage_argument(runner, abitrary_address):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
            " --validators-required-percent 20"
        ),
    )

    assert result.exit_code == 0
