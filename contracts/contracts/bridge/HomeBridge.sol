pragma solidity ^0.5.8;

import "../tlc-validator/ValidatorProxy.sol";

contract HomeBridge {
    struct TransferState {
        mapping(address => bool) isConfirmedByValidator;
        address payable[] confirmingValidators;
        uint16 numConfirmations;
        bool isCompleted;
    }

    event Confirmation(
        bytes32 transferHash,
        bytes32 transactionHash,
        uint256 amount,
        address recipient,
        address validator
    );
    event TransferCompleted(
        bytes32 transferHash,
        bytes32 transactionHash,
        uint256 amount,
        address recipient
    );

    mapping(bytes32 => TransferState) public transferState;
    ValidatorProxy validatorProxy;
    uint public validatorsRequiredPercent;

    constructor(ValidatorProxy _proxy, uint _validatorsRequiredPercent) public {
        require(
            address(_proxy) != address(0),
            "proxy must not be the zero address!"
        );
        require(
            _validatorsRequiredPercent >= 0 &&
                _validatorsRequiredPercent <= 100,
            "_validatorsRequiredPercent must be between 0 and 100"
        );
        validatorProxy = _proxy;
        validatorsRequiredPercent = _validatorsRequiredPercent;
    }

    function confirmTransfer(
        bytes32 transferHash,
        bytes32 transactionHash,
        uint256 amount,
        address payable recipient
    ) public {
        require(
            validatorProxy.isValidator(msg.sender),
            "must be validator to confirm transfers"
        );
        require(
            recipient != address(0),
            "recipient must not be the zero address!"
        );
        require(amount > 0, "amount must not be zero");

        // We compute a keccak hash for the transfer and use that as an identifier for the transfer
        bytes32 transferStateId = keccak256(
            abi.encodePacked(transferHash, transactionHash, amount, recipient)
        );

        bool isCompleted = _confirmTransfer(transferStateId, msg.sender);

        if (isCompleted) {
            recipient.transfer(amount);
        }

        // We have to emit the events here, because _confirmTransfer
        // doesn't even receive the necessary information to do it on
        // it's own

        emit Confirmation(
            transferHash,
            transactionHash,
            amount,
            recipient,
            msg.sender
        );
        if (isCompleted) {
            emit TransferCompleted(
                transferHash,
                transactionHash,
                amount,
                recipient
            );
        }
    }

    function _checkSufficientNumberOfConfirmations(uint16 numConfirmations)
        internal
        view
        returns (bool)
    {
        uint numRequired = (
                validatorProxy.numberOfValidators() *
                    validatorsRequiredPercent +
                    99
            ) /
            100;
        return numConfirmations >= numRequired;
    }

    function _confirmTransfer(
        bytes32 transferStateId,
        address payable validator
    ) internal returns (bool) {
        require(
            !transferState[transferStateId].isCompleted,
            "transfer already completed"
        );
        require(
            !transferState[transferStateId].isConfirmedByValidator[validator],
            "transfer already confirmed by validator"
        );

        transferState[transferStateId].isConfirmedByValidator[validator] = true;
        transferState[transferStateId].confirmingValidators.push(validator);
        transferState[transferStateId].numConfirmations += 1;

        if (
            _checkSufficientNumberOfConfirmations(
                transferState[transferStateId].numConfirmations
            )
        ) {
            transferState[transferStateId].isCompleted = true;
            return true;
        }
        return false;
    }
}
