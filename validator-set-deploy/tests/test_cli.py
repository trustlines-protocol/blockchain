import pytest
import csv

from click.testing import CliRunner
from eth_utils import to_checksum_address

from validator_set_deploy.cli import main


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture()
def validators_file(tmp_path, validator_list):
    folder = tmp_path / "subfolder"
    folder.mkdir()
    file_path = folder / "validators.csv"

    with file_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerows([[to_checksum_address(address)] for address in validator_list])

    return file_path


def test_deploy(runner, validators_file):

    result = runner.invoke(
        main, args=f"deploy --jsonrpc test --validators {validators_file}"
    )

    print(result.output)
    assert result.exit_code == 0
