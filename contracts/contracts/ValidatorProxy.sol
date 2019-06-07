pragma solidity ^0.5.8;

import "./ValidatorSet.sol";


/**
    This contract gives access to an up to date validator set on chain, that can be used by any other contracts.
    Its validator set is to be updated by validators contracts when the system address calls finalizeChange().
    This way, the `validators` array in this contract should remain correct throughout forks.
*/

contract ValidatorProxy {

    mapping (address => bool) public isValidator;
    address public systemAddress = 0xffffFFFfFFffffffffffffffFfFFFfffFFFfFFfE;
    address[] public validators;

    constructor(ValidatorSet validatorSet) public {
        require(validatorSet.finalized(), "The given validatorSet to initialize the validators is not finalized.");
        validators = validatorSet.getValidators();
    }

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
