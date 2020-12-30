pragma solidity ^0.6.5;

import "./ValidatorProxy.sol";

contract TestValidatorProxy is ValidatorProxy {
    constructor(address[] memory _validators, address _systemAddress)
        public
        ValidatorProxy(_validators)
    {
        systemAddress = _systemAddress;
    }
}
