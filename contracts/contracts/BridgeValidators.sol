pragma solidity ^0.5.8;

import "./lib/IBridgeValidators.sol";
import "./ValidatorProxy.sol";


contract BridgeValidators is IBridgeValidators {

    ValidatorProxy public validatorProxy;
    uint public requiredSignatureDivisor;
    uint public requiredSignatureMultiplier;

    constructor(ValidatorProxy _validatorProxy, uint _requiredSignatureDivisor, uint _requiredSignatureMultiplier) public {
        validatorProxy = _validatorProxy;
        requiredSignatureDivisor = _requiredSignatureDivisor;
        requiredSignatureMultiplier = _requiredSignatureMultiplier;
    }

    function isValidator(address _validator) public view returns(bool) {
        return validatorProxy.isValidator(_validator);
    }

    function requiredSignatures() public view returns(uint256) {
        numberOfValidators = validatorProxy.numberOfValidators();
        return numberOfValidators * _requiredSignatureMultiplier / _requiredSignatureDivisor;
    }

    function owner() public view returns(address) {
        return address(0);
    }
}
