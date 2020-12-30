pragma solidity ^0.6.5;

/**
    This contract gives access to an up to date validator set on chain, that can be used by any other contracts.
    Its validator set is to be updated by validators contracts when the system address calls finalizeChange().
    This way, the `validators` array in this contract should remain correct throughout forks.
*/

contract ValidatorProxy {
    mapping(address => bool) public isValidator;
    address public systemAddress = 0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE;
    address[] public validators;

    constructor(address[] memory _validators) public {
        validators = _validators;

        for (uint i = 0; i < _validators.length; i++) {
            isValidator[_validators[i]] = true;
        }
    }

    function updateValidators(address[] memory newValidators) public {
        require(
            tx.origin == systemAddress, // solium-disable-line security/no-tx-origin
            "Only the system address can be responsible for the call of this function."
        );

        for (uint i = 0; i < validators.length; i++) {
            isValidator[validators[i]] = false;
        }

        for (uint i = 0; i < newValidators.length; i++) {
            isValidator[newValidators[i]] = true;
        }

        validators = newValidators;
    }

    function numberOfValidators() public view returns (uint) {
        return validators.length;
    }

    function getValidators() public view returns (address[] memory) {
        return validators;
    }
}
