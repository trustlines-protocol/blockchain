#! pytest

import pytest
import itertools
import eth_tester.exceptions
from eth_utils.address import is_same_address
from .data_generation import make_equivocated_signed_block_header


STEP_DURATION = 5  # Value in seconds
MAX_UINT = 2 ** 256 - 1  # Maximum uint256 value in Solidity


def test_get_signer_address_valid(
    equivocation_inspector_contract_session,
    equivocated_signed_block_header_malicious_validator,
    malicious_validator_address,
):

    """Test the address recovery for signatures.

    Since the generated blocks use the same address for the signing the block as
    well as getting the reward, it is possible to compare the outcome of the
    recovery with the content of the block header.
    """

    address_recovered = equivocation_inspector_contract_session.functions.testGetSignerAddress(
        equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
        equivocated_signed_block_header_malicious_validator.signature,
    ).call()

    assert is_same_address(address_recovered, malicious_validator_address)


def test_fail_prove_equivcation_for_duplicated_block(
    equivocation_inspector_contract_session,
    equivocated_signed_block_header_malicious_validator,
):
    """Test different blocks rule.

    Case with two times the same block.
    Expected to fail cause the different blocks rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_validator.signature,
            equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_validator.signature,
        ).call()


def test_fail_prove_equivocation_for_incorrect_block_header_structure(
    equivocation_inspector_contract_session,
    equivocated_signed_block_header_malicious_validator,
    equivocated_signed_block_header_incorrect_structure,
):

    """Test header structure type.

    Case with a block header which has not the format of a list.
    Expected to fail cause the encoded header could not be decoded correctly.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_validator.signature,
            equivocated_signed_block_header_incorrect_structure.unsignedBlockHeader,
            equivocated_signed_block_header_incorrect_structure.signature,
        ).call()


def test_fail_prove_equivocation_for_too_short_block_header(
    equivocation_inspector_contract_session,
    equivocated_signed_block_header_malicious_validator,
    equivocated_signed_block_header_short_list,
):

    """Test header length rule.

    Case with a block header which has not enough entries to be accepted.
    Expected to fail cause the header length rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_validator.signature,
            equivocated_signed_block_header_short_list.unsignedBlockHeader,
            equivocated_signed_block_header_short_list.signature,
        ).call()


def test_fail_prove_equivocation_for_different_block_signers(
    equivocation_inspector_contract_session,
    equivocated_signed_block_header_malicious_validator,
    equivocated_signed_block_header_malicious_non_validator,
):

    """Test equal signer rule.

    Test with two equal block headers, but singed by different addresses.
    Expected to fail cause the equal signer rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            equivocated_signed_block_header_malicious_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_validator.signature,
            equivocated_signed_block_header_malicious_non_validator.unsignedBlockHeader,
            equivocated_signed_block_header_malicious_non_validator.signature,
        ).call()


@pytest.mark.parametrize(
    "signed_block_header_one, signed_block_header_two",
    [
        (
            make_equivocated_signed_block_header(timestamp=1.5 * STEP_DURATION),
            make_equivocated_signed_block_header(timestamp=timestamp),
        )
        for timestamp in [1, STEP_DURATION - 1, 2 * STEP_DURATION, MAX_UINT]
    ],
)
def test_fail_prove_equivocation_for_different_block_step(
    equivocation_inspector_contract_session,
    signed_block_header_one,
    signed_block_header_two,
):

    """Test equal block step rule.

    Case with two blocks which fulfill all equivocation rules, except the equal block step.
    Expected to fail cause the equal slot rule for equivocation could not been verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            signed_block_header_one.unsignedBlockHeader,
            signed_block_header_one.signature,
            signed_block_header_two.unsignedBlockHeader,
            signed_block_header_two.signature,
        ).call()


@pytest.mark.parametrize(
    "signed_block_header_one, signed_block_header_two",
    [
        (
            make_equivocated_signed_block_header(timestamp=timestamp_one),
            make_equivocated_signed_block_header(timestamp=timestamp_two),
        )
        for timestamp_one, timestamp_two in itertools.product(
            [
                STEP_DURATION,
                STEP_DURATION + 1,
                2 * STEP_DURATION - 2,
                2 * STEP_DURATION - 1,
            ],
            repeat=2,
        )
    ],
)
def test_prove_equivocation_successfully(
    equivocation_inspector_contract_session,
    signed_block_header_one,
    signed_block_header_two,
):

    """Test full equivocation proof.

    Test with two blocks with fulfill all rules of equivocation.
    Expected to run through without exception cause all rules can be verified.
    """

    equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
        signed_block_header_one.unsignedBlockHeader,
        signed_block_header_one.signature,
        signed_block_header_two.unsignedBlockHeader,
        signed_block_header_two.signature,
    ).call()
