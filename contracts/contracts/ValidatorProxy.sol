pragma solidity ^0.5.8;


contract ValidatorProxy {

    mapping (address => bool) public isValidator;
    address public systemAddress = 0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE;
    address[] public validators;

    function updateValidators(address[] memory newValidators) public {
        require(tx.origin == systemAddress, "Only the system address can be responsible for the call of this function.");  // solium-disable-line security/no-tx-origin

        for (uint i = 0; i < validators.length; i++) {
            isValidator[validators[i]] = false;
        }

        for (uint i = 0; i < newValidators.length; i++) {
            isValidator[newValidators[i]] = true;
        }

        validators = newValidators;
    }

    function numberOfValidators() public returns(uint) {
        return validators.length;
    }

    function getValidators() public returns(address[] memory) {
        return validators;
    }
}
