pragma solidity ^0.5.7;

import "./lib/Ownable.sol";
import "./DepositLockerInterface.sol";
import "./EquivocationInspector.sol";


contract ValidatorSlasher is Ownable {

    bool public initialized = false;
    DepositLockerInterface public depositContract;

    function() external {}

    function init(address _depositContractAddress) external onlyOwner returns (bool _success) {
        require(! initialized, "The contract is already initialized.");

        depositContract = DepositLockerInterface(_depositContractAddress);

        initialized = true;
        return true;
    }

    /**
     * Report a malicious validator for having equivocated.
     * The reporter must provide the both blocks with their related signature.
     * By the given blocks, the equivocation will be verified.
     * In case a equivocation could been proven, the issuer of the blocks get
     * removed from the set of validators, if his address is registered. Also
     * his deposit will be slashed afterwards.
     * In case any check before removing the malicious validator fails, the
     * whole report procedure fails due to that.
     *
     * @param _rlpUnsignedHeaderOne   the RLP encoded header of the first block
     * @param _signatureOne           the signature related to the first block
     * @param _rlpUnsignedHeaderTwo   the RLP encoded header of the second block
     * @param _signatureTwo           the signature related to the second block
     */
    function reportMaliciousValidator(
        bytes calldata _rlpUnsignedHeaderOne,
        bytes calldata _signatureOne,
        bytes calldata _rlpUnsignedHeaderTwo,
        bytes calldata _signatureTwo
    )
        external
    {
        EquivocationInspector.verifyEquivocationProof(
            _rlpUnsignedHeaderOne,
            _signatureOne,
            _rlpUnsignedHeaderTwo,
            _signatureTwo
        );

        // Since the proof has already verified, that both blocks have been
        // issued by the same validator, it doesn't matter which one is used here
        // to recover the address.
        address validator = EquivocationInspector.getSignerAddress(
            _rlpUnsignedHeaderOne,
            _signatureOne
        );

        depositContract.slash(validator);
    }
}
