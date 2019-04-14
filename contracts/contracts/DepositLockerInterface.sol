pragma solidity ^0.4.25;


contract DepositLockerInterface {

    function slash(address _depositorToBeSlashed) public returns (bool _success);
}
