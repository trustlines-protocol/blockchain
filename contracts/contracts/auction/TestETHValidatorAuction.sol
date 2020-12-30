pragma solidity ^0.6.5;

/*
  The sole purpose of this contract is to be able to test the auction without having to bother with price
*/

import "./ETHValidatorAuction.sol";

contract TestETHValidatorAuction is ETHValidatorAuction {
    constructor(BaseDepositLocker _depositLocker)
        public
        ETHValidatorAuction(100, 14, 50, 123, _depositLocker)
    {}

    function currentPrice() public view override returns (uint) {
        return 100;
    }
}
