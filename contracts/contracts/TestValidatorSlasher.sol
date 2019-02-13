pragma solidity ^0.4.25;

/*
  The sole purpose of this file is to be able to test the internal functions of the ValidatorSlasher
*/


import "./ValidatorSlasher.sol";


contract TestValidatorSlasher is ValidatorSlasher {

    constructor() public {
    }

    function() external {}

    function testRemoveValidatorFromSet(address _validator) public returns (bool _success) {
        return removeValidatorFromSet(_validator);
    }
}
