pragma solidity ^0.5.8;

contract TestRecipient {
    event GasLeft(uint gasLeft);

    function() external payable {
        emit GasLeft(gasleft());
    }
}

contract TestTransfer {
    function() external payable {}

    function doit(address payable recipient) public returns (bool) {
        bool res = true;

        /* solium-disable-next-line */
        (res, ) = recipient.call.value(1).gas(60000)("");

        // res = recipient.send(1);
        return res;
    }
}
