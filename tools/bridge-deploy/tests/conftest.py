import pytest


@pytest.fixture(scope="session")
def abitrary_address():
    """An unspecific Ethereum address for multiple use cases

    Meant to be used where ever any address is required but must not fulfill
    special requirements.
    """
    return "0x5757957701948584cc2A8293857D89b19De44f0F"
