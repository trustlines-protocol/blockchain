pragma solidity ^0.4.25;

/*
  The sole purpose of this contract is to be able to test the auction without having to bother with price
*/


import "./ValidatorAuction.sol";


contract TestValidatorAuctionFixedPrice is ValidatorAuction {

    function currentPrice() public view returns (uint) {
        return 100;
    }
}
