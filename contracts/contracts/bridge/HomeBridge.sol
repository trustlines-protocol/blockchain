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
        address indexed validator
    );
    event TransferCompleted(
        bytes32 transferHash,
        bytes32 transactionHash,
        uint256 amount,
        address recipient,
        bool coinTransferSuccessful
    );

    mapping(bytes32 => TransferState) public transferState;
    ValidatorProxy public validatorProxy;
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

    function fund() external payable {}

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
            bool coinTransferSuccessful = recipient.send(amount);
            emit TransferCompleted(
                transferHash,
                transactionHash,
                amount,
                recipient,
                coinTransferSuccessful
            );
        }
    }

    function purgeConfirmationsFromExValidators(bytes32 transferStateId)
        internal
    {
        address payable[] storage confirmingValidators = transferState[transferStateId]
            .confirmingValidators;

        uint i = 0;
        while (i < confirmingValidators.length) {
            if (validatorProxy.isValidator(confirmingValidators[i])) {
                i++;
            } else {
                confirmingValidators[i] = confirmingValidators[confirmingValidators
                        .length -
                    1];
                delete confirmingValidators[confirmingValidators.length - 1];
                confirmingValidators.length--;
                transferState[transferStateId].numConfirmations--;
            }
        }
    }

    function getNumRequiredConfirmations() internal view returns (uint) {
        return
            (
                    validatorProxy.numberOfValidators() *
                        validatorsRequiredPercent +
                        99
                ) /
                100;
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

        uint numRequired = getNumRequiredConfirmations();

        /* We now check if we have enough confirmations.  If that is the
           case, we purge ex-validators from the list of confirmations
           and do the check again, so we do not count
           confirmations from ex-validators.

           This means that old confirmations stay valid over validator set changes given
           that the validator doesn't loose it's validator status.

           The double check is here to save some gas. If checking the validator
           status for all confirming validators becomes too costly, we can introduce
           a 'serial number' for the validator set changes and determine if there
           was a change of the validator set between the first confirmation
           and the last confirmation and skip calling into
           purgeConfirmationsFromExValidators if there were no changes.
        */

        if (transferState[transferStateId].numConfirmations < numRequired) {
            return false;
        }

        purgeConfirmationsFromExValidators(transferStateId);

        if (transferState[transferStateId].numConfirmations < numRequired) {
            return false;
        }

        transferState[transferStateId].isCompleted = true;
        return true;
    }
}
