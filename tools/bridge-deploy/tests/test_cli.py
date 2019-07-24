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


def test_deploy_home(runner, abitrary_address):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home_with_valid_required_percentage_argument_lower_bound(
    runner, abitrary_address
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
            " --validators-required-percent 0"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home_with_valid_required_percentage_argument_upper_bound(
    runner, abitrary_address
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
            " --validators-required-percent 100"
        ),
    )

    assert result.exit_code == 0


def test_deploy_home_with_invalid_required_percentage_argument_lower_bound(
    runner, abitrary_address
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
            " --validators-required-percent -1"
        ),
    )

    assert result.exit_code == 2


def test_deploy_home_with_invalid_required_percentage_argument_upper_bound(
    runner, abitrary_address
):
    result = runner.invoke(
        main,
        args=(
            "deploy-home --jsonrpc test"
            f" --validator-proxy-address {abitrary_address}"
            " --validators-required-percent 101"
        ),
    )

    assert result.exit_code == 2
