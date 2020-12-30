pragma solidity ^0.6.5;

contract TestNonPayableRecipient {
    receive() external payable {
        require(false, "do not pay me");
    }
}
