pragma solidity ^0.5.8;

import "./ValidatorProxy.sol";


contract TestValidatorProxy is ValidatorProxy {

    constructor (address[] memory _validators, address _systemAddress) ValidatorProxy(_validators) public {
        systemAddress = _systemAddress;
    }
}
