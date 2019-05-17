pragma solidity ^0.5.7;


contract DepositLockerInterface {

    function slash(address _depositorToBeSlashed) public returns (bool _success);

}
