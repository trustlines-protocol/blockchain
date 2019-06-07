pragma solidity ^0.5.8;

import "./ValidatorProxy.sol";


contract TestValidatorProxy is ValidatorProxy {

    constructor (address _systemAddress) public {
        systemAddress = _systemAddress;
    }
}
