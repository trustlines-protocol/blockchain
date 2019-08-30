import os

import pytest

from bridge import config
from bridge.utils import get_validator_private_key


@pytest.fixture
def validator_private_key_bytes():
    return b"\x18\x88\xcf\xbal\xa6dxY\x8d\xc6_\xa9\x1b\xfc\xe1'*\x00SCu\x1f\xa0+\xa6'\x1b8\xac\x8e\x08"


@pytest.fixture
def validator_private_key_raw():
    return "0x1888cfba6ca66478598dc65fa91bfce1272a005343751fa02ba6271b38ac8e08"


@pytest.fixture
def keystore_folder():
    return os.path.dirname(os.path.realpath(__file__))


@pytest.fixture
def not_existing_path():
    return "/does/not/exist"


@pytest.fixture
def validator_private_key_keystore_path(keystore_folder):
    keystore_path = os.path.join(keystore_folder, "keystore.json")
    assert os.path.isfile(keystore_path)
    return keystore_path


@pytest.fixture
def validator_private_key_keystore_password_path(keystore_folder):
    keystore_password_path = os.path.join(keystore_folder, "password")
    assert os.path.isfile(keystore_password_path)
    return keystore_password_path


@pytest.fixture
def validator_private_key_keystore_password_path_not_matching(tmp_path):
    not_matching_password_file_path = tmp_path / "password_not_matching"
    not_matching_password_file_path.write_text("not-correct")
    print(not_matching_password_file_path)
    return not_matching_password_file_path


@pytest.fixture
def configuration_with_validator_private_key_raw(validator_private_key_raw):
    return {
        "validator_private_key": config.PrivateKeySchema().load(
            {"raw": validator_private_key_raw}
        )
    }


@pytest.fixture
def configuration_with_validator_private_key_keystore(
    validator_private_key_keystore_path, validator_private_key_keystore_password_path
):
    return {
        "validator_private_key": {
            "keystore_path": validator_private_key_keystore_path,
            "keystore_password_path": validator_private_key_keystore_password_path,
        }
    }


def test_get_validator_validator_private_key_raw(
    configuration_with_validator_private_key_raw, validator_private_key_bytes
):
    assert (
        get_validator_private_key(configuration_with_validator_private_key_raw)
        == validator_private_key_bytes
    )


def test_get_validator_private_key_kestore(
    configuration_with_validator_private_key_keystore, validator_private_key_bytes
):
    assert (
        get_validator_private_key(configuration_with_validator_private_key_keystore)
        == validator_private_key_bytes
    )


def test_get_validator_private_key_kestore_not_existing_keystore_path(
    configuration_with_validator_private_key_keystore, not_existing_path
):
    configuration_with_validator_private_key_keystore["validator_private_key"][
        "keystore_path"
    ] = not_existing_path

    with pytest.raises(ValueError):
        get_validator_private_key(configuration_with_validator_private_key_keystore)


def test_get_validator_private_key_kestore_not_existing_keystore_password_path(
    configuration_with_validator_private_key_keystore, not_existing_path
):
    configuration_with_validator_private_key_keystore["validator_private_key"][
        "keystore_password_path"
    ] = not_existing_path

    with pytest.raises(ValueError):
        get_validator_private_key(configuration_with_validator_private_key_keystore)


def test_get_validator_private_key_kestore_not_matching_password(
    configuration_with_validator_private_key_keystore,
    validator_private_key_keystore_password_path_not_matching,
):
    configuration_with_validator_private_key_keystore["validator_private_key"][
        "keystore_password_path"
    ] = validator_private_key_keystore_password_path_not_matching

    with pytest.raises(ValueError):
        get_validator_private_key(configuration_with_validator_private_key_keystore)
