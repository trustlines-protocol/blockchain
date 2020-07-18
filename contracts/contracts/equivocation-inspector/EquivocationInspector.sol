pragma solidity ^0.5.8;

import "../lib/RLPReader.sol";
import "../lib/ECDSA.sol";

/**
 * Utilities to verify equivocating behavior of validators.
 */
library EquivocationInspector {
    using RLPReader for RLPReader.RLPItem;
    using RLPReader for bytes;

    uint constant STEP_DURATION = 5;

    /**
     * Get the signer address for a given signature and the related data.
     *
     * @dev Used as abstraction layer to the ECDSA library.
     *
     * @param _data       the data the signature is for
     * @param _signature  the signature the address should be recovered from
     */
    function getSignerAddress(bytes memory _data, bytes memory _signature)
        internal
        pure
        returns (address)
    {
        bytes32 hash = keccak256(_data);
        return ECDSA.recover(hash, _signature);
    }

    /**
     * Verify malicious behavior of an authority.
     * Prove the presence of equivocation by two given blocks.
     * Equivocation is proven by:
     *    - two different blocks have been provided
     *    - both signatures have been issued by the same address
     *    - the step of both blocks is the same
     *
     * Block headers provided as arguments do not include their signature within.
     * By design this is expected to be the source that has been signed.
     *
     * The function fails if the proof can not be verified.
     * In case the proof can be verified, the function returns nothing.
     *
     * @dev Implement the rules of an equivocation.
     *
     * @param _rlpUnsignedHeaderOne   the RLP encoded header of the first block
     * @param _signatureOne           the signature related to the first block
     * @param _rlpUnsignedHeaderTwo   the RLP encoded header of the second block
     * @param _signatureTwo           the signature related to the second block
     */
    function verifyEquivocationProof(
        bytes memory _rlpUnsignedHeaderOne,
        bytes memory _signatureOne,
        bytes memory _rlpUnsignedHeaderTwo,
        bytes memory _signatureTwo
    ) internal pure {
        // Make sure two different blocks have been provided.
        bytes32 hashOne = keccak256(_rlpUnsignedHeaderOne);
        bytes32 hashTwo = keccak256(_rlpUnsignedHeaderTwo);

        // Different block rule.
        require(
            hashOne != hashTwo,
            "Equivocation can be proved for two different blocks only."
        );

        // Parse the RLP encoded block header list.
        // Note that this can fail here, if the block header has no list format.
        RLPReader.RLPItem[] memory blockOne = _rlpUnsignedHeaderOne
            .toRlpItem()
            .toList();
        RLPReader.RLPItem[] memory blockTwo = _rlpUnsignedHeaderTwo
            .toRlpItem()
            .toList();

        // Header length rule.
        // Keep it open ended, since they could contain a list of empty messages for finality.
        require(
            blockOne.length >= 12 && blockTwo.length >= 12,
            "The number of provided header entries are not enough."
        );

        // Equal signer rule.
        require(
            getSignerAddress(_rlpUnsignedHeaderOne, _signatureOne) ==
                getSignerAddress(_rlpUnsignedHeaderTwo, _signatureTwo),
            "The two blocks have been signed by different identities."
        );

        // Equal block step rule.
        uint stepOne = blockOne[11].toUint() / STEP_DURATION;
        uint stepTwo = blockTwo[11].toUint() / STEP_DURATION;

        require(stepOne == stepTwo, "The two blocks have different steps.");
    }
}
