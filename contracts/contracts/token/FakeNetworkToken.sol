/*
This contract is only used for testing. It emits Transfer events just
like the TrustlinesNetworkToken contract.

It can be deployed with the following command

    deploy-tools deploy FakeNetworkToken

Please note that all of the functions are public.
*/

pragma solidity ^0.5.8;

contract FakeNetworkToken {
    event Transfer(address indexed from, address indexed to, uint256 value);

    function transfer(address from, address to, uint256 value) public {
        emit Transfer(from, to, value);
    }

    /* emit multiple events in a single transaction */
    function transfer4(address from, address to, uint256 value) public {
        emit Transfer(from, to, value);
        emit Transfer(from, to, value);

        emit Transfer(from, to, value + 1);
        emit Transfer(from, to, value + 2);
    }
}
