pragma solidity ^0.4.25;


contract DepositLockerInterface {

    function slash(address _validator) public returns (bool _success);
}
