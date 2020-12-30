pragma solidity ^0.7.0;

contract TestNonPayableRecipient {
    receive() external payable {
        require(false, "do not pay me");
    }
}
