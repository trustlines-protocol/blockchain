import pytest

from click.testing import CliRunner

from validator_set_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


def test_dummy(runner):

    result = runner.invoke(main, args="deploy --jsonrpc test")

    assert result.exit_code == 0
