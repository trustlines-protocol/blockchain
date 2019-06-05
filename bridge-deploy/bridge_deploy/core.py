from eth_utils import is_address, to_checksum_address


def validate_and_format_address(address):  # TODO: refactor this into deploy_tools
    """Validates the address and formats it into the internal format
    Will raise `InvalidAddressException, if the address is invalid"""
    if is_address(address):
        return to_checksum_address(address)
    else:
        raise InvalidAddressException()


class InvalidAddressException(Exception):  # TODO: refactor this into deploy_tools
    pass
