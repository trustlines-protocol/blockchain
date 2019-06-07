pragma solidity ^0.5.8;

import "./lib/IBridgeValidators.sol";
import "./ValidatorProxy.sol";


contract BridgeValidators is IBridgeValidators {

    ValidatorProxy public validatorProxy;
    uint public requiredSignaturesDivisor;
    uint public requiredSignaturesMultiplier;

    constructor(ValidatorProxy _validatorProxy, uint _requiredSignaturesDivisor, uint _requiredSignaturesMultiplier) public {
        validatorProxy = _validatorProxy;
        requiredSignaturesDivisor = _requiredSignaturesDivisor;
        requiredSignaturesMultiplier = _requiredSignaturesMultiplier;
    }

    function isValidator(address _validator) public view returns(bool) {
        return validatorProxy.isValidator(_validator);
    }

    function requiredSignatures() public returns(uint256) {
        uint numberOfValidators = validatorProxy.numberOfValidators();
        return numberOfValidators * requiredSignaturesMultiplier / requiredSignaturesDivisor;
    }

    function owner() public view returns(address) {
        return address(0);
    }
}
