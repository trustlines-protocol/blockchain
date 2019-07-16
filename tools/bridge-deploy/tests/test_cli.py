import pytest

from click.testing import CliRunner

from bridge_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_deploy_foreign(runner):

    result = runner.invoke(
        main,
        args="deploy-foreign --jsonrpc test --token-address 0x5757957701948584cc2A8293857D89b19De44f0F",
    )

    assert result.exit_code == 0


def test_print_foreign(runner):

    result = runner.invoke(main, args="print-foreign --jsonrpc test")

    assert result.exit_code == 0
