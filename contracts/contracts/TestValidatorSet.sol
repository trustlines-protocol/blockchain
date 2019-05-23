pragma solidity ^0.4.25;

/*
  The sole purpose of this file is to be able to test the internal functions of the ValidatorSet
*/


import "./ValidatorSet.sol";


contract TestValidatorSet is ValidatorSet {

    function testRemoveValidator(address _validator) public returns (bool _success) {
        return removeValidator(_validator);
    }

    /**
     * @dev Intended to test the functionality of finalizing the validator set
     *      without the need to report a validator, which is the only opportunity to
     *      change the set in the origin contract.
     */
    function testChangeValiatorSet(address[] _newValidatorSet) public {
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
