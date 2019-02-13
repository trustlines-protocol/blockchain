pragma solidity ^0.4.25;

/*
  The sole purpose of this file is to be able to test the internal functions of the ValidatorSet
*/


import "./ValidatorSet.sol";


contract TestValidatorSet is ValidatorSet {

    constructor() public {
    }

    function() external {}

    function testRemoveValidator(address _validator) public returns (bool _success) {
        return removeValidator(_validator);
    }

}
