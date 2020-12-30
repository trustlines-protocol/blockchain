pragma solidity ^0.8.0;

/*
  The sole purpose of this file is to be able to test the internal functions of the EquivocationInspector.
*/

import "./EquivocationInspector.sol";

contract TestEquivocationInspector {
    function testGetSignerAddress(bytes memory _data, bytes memory _signature)
        public
        pure
        returns (address)
    {
        return EquivocationInspector.getSignerAddress(_data, _signature);
    }

    function testVerifyEquivocationProof(
        bytes memory _rlpBlockOne,
        bytes memory _signatureOne,
        bytes memory _rlpBlockTwo,
        bytes memory _signatureTwo
    ) public pure {
        EquivocationInspector.verifyEquivocationProof(
            _rlpBlockOne,
            _signatureOne,
            _rlpBlockTwo,
            _signatureTwo
        );
    }
}

// SPDX-License-Identifier: MIT
