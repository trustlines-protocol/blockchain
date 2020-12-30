pragma solidity ^0.8.0;

contract TestNonPayableRecipient {
    receive() external payable {
        require(false, "do not pay me");
    }
}

// SPDX-License-Identifier: MIT
