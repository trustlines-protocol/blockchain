#! pytest

import pytest
import eth_tester.exceptions
from eth_utils.address import is_same_address


def test_get_signer_address_valid(
    equivocation_inspector_contract_session,
    signed_block_header_one,
    signed_block_header_one_address,
):

    """Test the address recovery for signatures.

    Since the issued blocks from the Koven test network have used the same address for the signing
    the block as well as getting the reward, it is possible to compare the outcome of the recovery
    with the content of the block header.
    """

    address_recovered = equivocation_inspector_contract_session.functions.testGetSignerAddress(
        signed_block_header_one.unsignedBlockHeader, signed_block_header_one.signature
    ).call()

    assert is_same_address(address_recovered, signed_block_header_one_address)


def test_fail_prove_equivcation_for_duplicated_block(
    equivocation_inspector_contract_session, signed_block_header_one
):

    """Test different blocks rule.

    Case with two times the same block.
    Expected to fail cause the different blocks rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            signed_block_header_one.unsignedBlockHeader,
            signed_block_header_one.signature,
            signed_block_header_one.unsignedBlockHeader,
            signed_block_header_one.signature,
        ).call()


def test_fail_prove_equivocation_for_incorrect_block_header_structure(
    equivocation_inspector_contract_session, two_signed_blocks_no_list_header
):

    """Test header structure type.

    Case with a block header which has not the format of a list.
    Expected to fail cause the encoded header could not be decoded correctly.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            two_signed_blocks_no_list_header[0].unsignedBlockHeader,
            two_signed_blocks_no_list_header[0].signature,
            two_signed_blocks_no_list_header[1].unsignedBlockHeader,
            two_signed_blocks_no_list_header[1].signature,
        ).call()


def test_fail_prove_equivocation_for_too_short_block_header(
    equivocation_inspector_contract_session, two_signed_blocks_too_short_header
):

    """Test header length rule.

    Case with a block header which has not enough entries to be accepted.
    Expected to fail cause the header length rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            two_signed_blocks_too_short_header[0].unsignedBlockHeader,
            two_signed_blocks_too_short_header[0].signature,
            two_signed_blocks_too_short_header[1].unsignedBlockHeader,
            two_signed_blocks_too_short_header[1].signature,
        ).call()


def test_fail_prove_equivocation_for_different_block_signers(
    equivocation_inspector_contract_session, two_signed_blocks_different_signer
):

    """Test equal signer rule.

    Test with two equal block headers, but singed by different addresses.
    Expected to fail cause the equal signer rule for equivocation could not be verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            two_signed_blocks_different_signer[0].unsignedBlockHeader,
            two_signed_blocks_different_signer[0].signature,
            two_signed_blocks_different_signer[1].unsignedBlockHeader,
            two_signed_blocks_different_signer[1].signature,
        ).call()


def test_fail_prove_equivocation_for_different_block_step(
    equivocation_inspector_contract_session, two_signed_blocks_different_block_step
):

    """Test equal block step rule.

    Case with two blocks which fulfill all equivocation rules, except the equal block step.
    Expected to fail cause the equal slot rule for equivocation could not been verified.
    """

    with pytest.raises(eth_tester.exceptions.TransactionFailed):
        equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
            two_signed_blocks_different_block_step[0].unsignedBlockHeader,
            two_signed_blocks_different_block_step[0].signature,
            two_signed_blocks_different_block_step[1].unsignedBlockHeader,
            two_signed_blocks_different_block_step[1].signature,
        ).call()


def test_prove_equivocation_successfully(
    equivocation_inspector_contract_session,
    sign_two_equivocating_block_header,
    malicious_validator_key,
):

    """Test full equivocation proof.

    Test with two blocks with fulfill all rules of equivocation.
    Expected to run through without exception cause all rules can be verified.
    """

    two_signed_blocks_equivocated_by_malicious_non_validator = sign_two_equivocating_block_header(
        malicious_validator_key
    )

    equivocation_inspector_contract_session.functions.testVerifyEquivocationProof(
        two_signed_blocks_equivocated_by_malicious_non_validator[0].unsignedBlockHeader,
        two_signed_blocks_equivocated_by_malicious_non_validator[0].signature,
        two_signed_blocks_equivocated_by_malicious_non_validator[1].unsignedBlockHeader,
        two_signed_blocks_equivocated_by_malicious_non_validator[1].signature,
    ).call()
