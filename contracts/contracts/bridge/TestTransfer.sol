pragma solidity ^0.5.8;

contract TestRecipient {
    uint public numCalls;
    function() external payable {
        numCalls += 1;
    }
}

contract TestTransfer {
    function() external payable {}

    function doit(address payable recipient) public returns (bool) {
        /* solium-disable-next-line */
        (bool res, ) = recipient.call.value(1).gas(80000)("");
        return res;
    }
}
