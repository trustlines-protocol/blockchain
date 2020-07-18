pragma solidity ^0.5.8;

contract TestNonPayableRecipient {
    function() external payable {
        require(false, "do not pay me");
    }
}
