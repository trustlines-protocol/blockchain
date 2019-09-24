pragma solidity ^0.5.8;

contract DepositLockerInterface {
    function slash(address _depositorToBeSlashed) public;

}
