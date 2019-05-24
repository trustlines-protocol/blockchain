import pytest
import csv
import re

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


@pytest.fixture()
def validators_file_missing_validators(tmp_path, validator_list):
    file_path = tmp_path / "validators_missing.csv"

    with file_path.open("w") as f:
        writer = csv.writer(f)
        writer.writerows(
            [
                [to_checksum_address(address)]
                for address in validator_list[: len(validator_list) // 2]
            ]
        )

    return file_path


@pytest.fixture()
def deployed_validator_contract_address(runner, validators_file):

    deploy_result = runner.invoke(
        main, args=f"deploy --jsonrpc test --validators {validators_file}"
    )

    if deploy_result.exception is not None:
        raise RuntimeError(
            "Error while trying to run auction-deploy"
        ) from deploy_result.exception

    return extract_validator_contract_address(deploy_result.output)


def extract_validator_contract_address(output):
    """extract the ValidatorSet address from 'deploy' output"""
    match = re.search("^ValidatorSet address: (0x[0-9a-fA-F]{40})$", output, re.M)
    if match:
        return match[1]

    raise ValueError(f"Could not find auction address in output: {repr(output)}")


def test_deploy(runner, validators_file):

    result = runner.invoke(
        main, args=f"deploy --jsonrpc test --validators {validators_file}"
    )

    print(result.output)
    assert result.exit_code == 0


def test_check_validators(runner, deployed_validator_contract_address, validators_file):

    result = runner.invoke(
        main,
        args=f"check-validators --jsonrpc test --address {deployed_validator_contract_address}"
        f" --validators {validators_file}",
    )

    print(result.output)
    assert result.exit_code == 0


def test_check_missing_validators(
    runner, deployed_validator_contract_address, validators_file_missing_validators
):

    result = runner.invoke(
        main,
        args=f"check-validators --jsonrpc test --address {deployed_validator_contract_address}"
        f" --validators {validators_file_missing_validators}",
    )

    print(result.output)
    assert result.exit_code == 0


def test_print_validators(runner, deployed_validator_contract_address, validators_file):

    result = runner.invoke(
        main,
        args=f"print-validators --jsonrpc test --address {deployed_validator_contract_address}",
    )

    print(result.output)
    assert result.exit_code == 0
