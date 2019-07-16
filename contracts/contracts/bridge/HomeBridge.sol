pragma solidity ^0.5.8;

import "../tlc-validator/ValidatorProxy.sol";

contract HomeBridge {
    struct TransferState {
        mapping(address => bool) isConfirmedByValidator;
        address payable[] confirmingValidators;
        uint16 numConfirmations;
        bool isCompleted;
    }

    event Confirmation(bytes32 transactionHash, uint256 amount, address recipient, address validator);

    event TransferCompleted(bytes32 transactionHash, uint256 amount, address recipient);

    mapping(bytes32 => TransferState) public transferState;
    ValidatorProxy validatorProxy;

    constructor(ValidatorProxy _proxy) public {
        require(address(_proxy) != address(0), "proxy must not be the zero address!");

        validatorProxy = _proxy;
    }

    /* We need the fallback function only for the tests at the
       moment. This will be removed later */
    function() external payable {}

    function confirmTransfer(bytes32 transactionHash, uint256 amount, address payable recipient) public {
        require(validatorProxy.isValidator(msg.sender), "must be validator to confirm transfers");
        require(recipient != address(0), "recipient must not be the zero address!");
        require(amount>0, "amount must not be zero");

        // We compute a keccak hash for the transfer and use that as an identifier for the transfer
        bytes32 transferHash = keccak256(abi.encodePacked(transactionHash, amount, recipient));

        bool isCompleted = _confirmTransfer(transferHash, msg.sender);

        if (isCompleted) {
            recipient.transfer(amount);
        }

        // We have to emit the events here, because _confirmTransfer
        // doesn't even receive the necessary information to do it on
        // it's own

        emit Confirmation(transactionHash, amount, recipient, msg.sender);
        if (isCompleted) {
            emit TransferCompleted(transactionHash, amount, recipient);
        }
    }

    function _checkSufficientNumberOfConfirmations(uint16 numConfirmations)
        internal pure
        returns (bool)
    {
        /* XXX We need to change this at some point */
        return numConfirmations >= 2;
    }

    function _confirmTransfer(bytes32 transferHash, address payable validator)
        internal
        returns (bool)
    {
        require(!transferState[transferHash].isCompleted, "transfer already completed");
        require(!transferState[transferHash].isConfirmedByValidator[validator], "transfer already confirmed");

        transferState[transferHash].isConfirmedByValidator[validator] = true;
        transferState[transferHash].confirmingValidators.push(validator);
        transferState[transferHash].numConfirmations += 1;

        if (_checkSufficientNumberOfConfirmations(transferState[transferHash].numConfirmations)) {
            transferState[transferHash].isCompleted = true;
            return true;
        }
        return false;
    }
}
