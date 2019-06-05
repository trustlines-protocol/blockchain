#! pytest
import pytest

import rlp
from web3 import Web3
import eth_tester.exceptions


@pytest.fixture(scope="session")
def test_rlp_reader_contract(deploy_contract):
    return deploy_contract("TestRLPReader")


def test_fails_empty_to_rlp_item(test_rlp_reader_contract):
    """test conversion function from rlp encoded integer to internal data struct RLPItem"""
    contract = test_rlp_reader_contract
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testToRlpItem(b"").call()


def test_int_to_rlp_item(test_rlp_reader_contract):
    """test conversion function from rlp encoded integer to internal data struct RLPItem"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode(1)
    rlp_item_from_contract = contract.functions.testToRlpItem(rlp_encoded_item).call()

    assert rlp_item_from_contract[0] == 1


def test_string_to_rlp_item(test_rlp_reader_contract):
    """test conversion function from rlp encoded string to internal data struct RLPItem"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode("dog")
    rlp_item_from_contract = contract.functions.testToRlpItem(rlp_encoded_item).call()

    assert rlp_item_from_contract[0] == 4


def test_list_to_rlp_item(test_rlp_reader_contract):
    """test conversion function from rlp encoded list to internal data struct RLPItem"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode(["cat", "dog"])
    rlp_item_from_contract = contract.functions.testToRlpItem(rlp_encoded_item).call()

    assert rlp_item_from_contract[0] == 9


def test_is_list_true(test_rlp_reader_contract):
    """test if rlp encoded item is list"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode([1, 2, 3])

    assert contract.functions.testIsList(rlp_encoded_item).call() is True


def test_is_list_false(test_rlp_reader_contract):
    """test if rlp encoded item is not a list"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode(1)

    assert contract.functions.testIsList(rlp_encoded_item).call() is False


def test_to_bytes(test_rlp_reader_contract):
    """test conversion function to bytes"""
    contract = test_rlp_reader_contract
    str_to_encode = "dog"
    rlp_encoded_item = rlp.encode(str_to_encode)

    assert contract.functions.testToBytes(rlp_encoded_item).call() == Web3.toBytes(
        text=str_to_encode
    )


def test_to_boolean(test_rlp_reader_contract):
    """test conversion function to boolean"""
    contract = test_rlp_reader_contract
    bool_as_num = 1
    rlp_encoded_item = rlp.encode(bool_as_num)

    assert contract.functions.testToBoolean(rlp_encoded_item).call() is True


def test_to_uint_small(test_rlp_reader_contract):
    """test conversion function to uint"""
    contract = test_rlp_reader_contract
    num = 1  # smaller than a byte
    rlp_encoded_item = rlp.encode(num)

    assert contract.functions.testToUint(rlp_encoded_item).call() == num


def test_to_uint_big(test_rlp_reader_contract):
    """test conversion function to uint"""
    contract = test_rlp_reader_contract
    num = 128  # larger than a byte
    rlp_encoded_item = rlp.encode(num)

    assert contract.functions.testToUint(rlp_encoded_item).call() == num


def test_get_uint_from_list(test_rlp_reader_contract):
    """test get and item from a list"""
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode([1, 2, 3])

    assert len(rlp_encoded_item) < 32
    assert contract.functions.testGetItemUint(1, rlp_encoded_item).call() == 2


def test_get_uint_from_big_list(test_rlp_reader_contract):
    """test get and item from a list"""
    contract = test_rlp_reader_contract
    list = [i * 2 ** 250 for i in range(3)]
    rlp_encoded_item = rlp.encode(list)

    assert len(rlp_encoded_item) > 32
    assert contract.functions.testGetItemUint(1, rlp_encoded_item).call() == list[1]


def test_to_address(test_rlp_reader_contract):
    """test conversion function to address"""
    contract = test_rlp_reader_contract
    zero_address = "0x0000000000000000000000000000000000000000"
    rlp_encoded_item = rlp.encode(20 * b"\00")

    assert contract.functions.testToAddress(rlp_encoded_item).call() == zero_address


def test_fails_get_uint_from_list_out_of_bounds(test_rlp_reader_contract):
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode([1, 2, 3])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testGetItemUint(4, rlp_encoded_item).call()


def test_fails_get_uint_from_empty_list_(test_rlp_reader_contract):
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode([])

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testGetItemUint(0, rlp_encoded_item).call()


def test_fails_get_uint_from_list_not_a_list(test_rlp_reader_contract):
    contract = test_rlp_reader_contract
    rlp_encoded_item = rlp.encode(3)

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testGetItemUint(0, rlp_encoded_item).call()


def test_fails_get_uint_from_list_empty_byte_string(test_rlp_reader_contract):
    contract = test_rlp_reader_contract

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testGetItemUint(0, b"").call()


def test_fails_to_uint_empty_byte_string(test_rlp_reader_contract):
    contract = test_rlp_reader_contract

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testToUint(b"").call()


def test_fails_to_boolean(test_rlp_reader_contract):
    contract = test_rlp_reader_contract

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testToBoolean(b"").call()


def test_fails_to_bytes_from_empty_byte_string(test_rlp_reader_contract):
    """test conversion function to bytes"""
    contract = test_rlp_reader_contract

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testToBytes(b"").call()


def test_fails_is_list_false_empty_byte_string(test_rlp_reader_contract):
    """test if rlp encoded item is list"""
    contract = test_rlp_reader_contract
    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        contract.functions.testIsList(b"").call()
