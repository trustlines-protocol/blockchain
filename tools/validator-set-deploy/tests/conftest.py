import pytest

from eth_utils import to_canonical_address


@pytest.fixture()
def validator_list():
    def create_address_string(i: int):
        return f"0x{str(i).rjust(40, '0')}"

    return [to_canonical_address(create_address_string(i)) for i in range(30)]
