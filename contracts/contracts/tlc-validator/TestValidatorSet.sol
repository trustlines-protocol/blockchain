pragma solidity ^0.5.8;

/*
  The sole purpose of this file is to be able to test the internal functions of the ValidatorSet
*/

import "./ValidatorSet.sol";


contract TestValidatorSet is ValidatorSet {
    constructor(address _systemAddress) public {
        systemAddress = _systemAddress;
    }

    function testRemoveValidator(address _validator) public {
        removeValidator(_validator);
    }

    /**
     * @dev Intended to test the functionality of finalizing the validator set
     *      without the need to report a validator, which is the only opportunity to
     *      change the set in the origin contract.
     */
    function testChangeValiatorSet(address[] memory _newValidatorSet) public {
        require(finalized, "Validator set change is already ongoing!");
        pendingValidators = _newValidatorSet;
        initiateChange(_newValidatorSet);
    }

    /**
     * @dev Allows the to finalize changes without the need to control the system
     *      address. This enables testing independent from Parity.
     */
    function testFinalizeChange() public {
        address originSystemAddress = systemAddress;
        systemAddress = msg.sender;
        finalizeChange();
        systemAddress = originSystemAddress;
    }
}
