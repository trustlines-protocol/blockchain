pragma solidity ^0.8.0;

import "./ValidatorProxy.sol";

contract TestValidatorProxy is ValidatorProxy {
    constructor(address[] memory _validators, address _systemAddress)
        ValidatorProxy(_validators)
    {
        systemAddress = _systemAddress;
    }
}
