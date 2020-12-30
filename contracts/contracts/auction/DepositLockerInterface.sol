pragma solidity ^0.7.0;

// It is not actually an interface regarding solidity because interfaces can only have external functions
abstract contract DepositLockerInterface {
    function slash(address _depositorToBeSlashed) public virtual;
}
