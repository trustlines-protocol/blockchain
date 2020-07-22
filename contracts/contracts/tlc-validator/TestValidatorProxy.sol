pragma solidity ^0.5.8;

import "./ValidatorProxy.sol";


contract TestValidatorProxy is ValidatorProxy {
    constructor(address[] memory _validators, address _systemAddress)
        public
        ValidatorProxy(_validators)
    {
        systemAddress = _systemAddress;
    }
}
