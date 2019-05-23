pragma solidity ^0.4.25;

import "./EquivocationInspector.sol";


contract ValidatorSet {

    /// Issue this log event to signal a desired change in validator set.
    /// This will not lead to a change in active validator set until
    /// finalizeChange is called.
    ///
    /// Only the last log event of any block can take effect.
    /// If a signal is issued while another is being finalized it may never
    /// take effect.
    ///
    /// _parent_hash here should be the parent block hash, or the
    /// signal will not be recognized.
    // do not modify this event, aura will likely bug
    event InitiateChange(bytes32 indexed _parentHash, address[] _newSet);

    struct AddressStatus {
        uint index;
        bool isValidator;
    }

    bool initiated = false;
    address[] currentValidators;
    address[] public pendingValidators;
    mapping(address => AddressStatus) status;
    bool public finalized;  // Was the last validator change finalized. Implies currentValidators == pendingValidators
    address public systemAddress = 0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE;
    uint[] epochStartHeights;
    mapping(uint => address[]) epochValidators;

    modifier onlySystem() {
        require(
            msg.sender == systemAddress,
            "The access is restricted to the system address only."
        );
        _;
    }

    modifier isFinalized() {
        require(
            finalized,
            "The last validator change must be finalized."
        );
        _;
    }

    function init(address[] _validators) external returns (bool _success) {
        require(
            !initiated,
            "Can not initate twice."
        );

        pendingValidators = _validators;

        for (uint i = 0; i < _validators.length; i++) {
            status[_validators[i]].isValidator = true;
            status[_validators[i]].index = i;
        }

        currentValidators = _validators;
        finalized = true;
        initiated = true;
        return true;
    }

    function getEpochStartHeights() external view returns(uint[]) {
        return epochStartHeights;
    }

    function getValidators(uint _epochStart) external view returns(address[]) {
        return epochValidators[_epochStart];
    }

    /**
     * Report a malicious validator for having equivocated.
     * The reporter must provide both blocks with their related signatures.
     * By the given blocks, the equivocation will be verified.
     * In case an equivocation could been proven, the issuer of the blocks get
     * removed from the set of validators, if his address is registered.
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
            status[validator].isValidator,
            "The reported address is not a validator."
        );

        removeValidator(validator);
    }

    // Get current validator set (last enacted or initial if no changes ever made)
    // do not modify this function, aura will likely bug
    function getValidators() public view returns (address[] _validators) {
        _validators = currentValidators;
    }

    /// Called when an initiated change reaches finality and is activated.
    /// Only valid when msg.sender == SUPER_USER (EIP96, 2**160 - 2)
    ///
    /// Also called when the contract is first enabled for consensus. In this case,
    /// the "change" finalized is the activation of the initial set.
    // do not modify this function, aura will likely bug
    function finalizeChange() public onlySystem {
        currentValidators = pendingValidators;
        finalized = true;
        epochStartHeights.push(block.number);
        epochValidators[block.number] = currentValidators;
    }

    function removeValidator(address _validator) internal isFinalized returns (bool _success) {
        require(
            status[_validator].isValidator,
            "The given address does not belong to a validator."
        );

        uint index = status[_validator].index;
        pendingValidators[index] = pendingValidators[pendingValidators.length - 1];
        status[pendingValidators[index]].index = index;
        delete pendingValidators[pendingValidators.length - 1];
        pendingValidators.length--;

        delete status[_validator];
        initiateChange(pendingValidators);
        return true;
    }

    function initiateChange(address[] _newValidatorSet) internal {
        finalized = false;
        emit InitiateChange(block.blockhash(block.number-1), _newValidatorSet);
    }

}
