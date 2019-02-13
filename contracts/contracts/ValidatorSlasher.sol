pragma solidity ^0.4.25;

import "./lib/Ownable.sol";
import "./lib/it_set_lib.sol";
import "./DepositLockerInterface.sol";
import "./EquivocationInspector.sol";


contract ValidatorSlasher is Ownable {

    bool initialised = false;
    using ItSet for ItSet.AddressSet;
    ItSet.AddressSet internal validatorItSet;
    DepositLockerInterface depositContract;

    function() external {}

    function init(address[] _validators, address _depositContractAddress) external onlyOwner returns (bool _success) {
        require(! initialised, "The contract is already initialised.");

        depositContract = DepositLockerInterface(_depositContractAddress);

        for (uint i = 0; i < _validators.length; i++) {
            validatorItSet.insert(_validators[i]);
        }

        initialised = true;
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
        bytes _rlpUnsignedHeaderOne,
        bytes _signatureOne,
        bytes _rlpUnsignedHeaderTwo,
        bytes _signatureTwo
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

        require(
            validatorItSet.contains(validator),
            "The reported address is not a validator."
        );

        removeValidatorFromSet(validator);
        depositContract.slash(validator);
    }

    function getValidator(uint index) public view returns(address) {
        return validatorItSet.list[index];
    }

    function removeValidatorFromSet(address _validator) internal returns (bool _success) {
        assert(validatorItSet.contains(_validator));

        validatorItSet.remove(_validator);
        return true;
    }
}
