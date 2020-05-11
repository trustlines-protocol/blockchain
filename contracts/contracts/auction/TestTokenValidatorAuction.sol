pragma solidity ^0.5.8;

/*
  The sole purpose of this contract is to be able to test the auction without having to bother with price
*/

import "./TokenValidatorAuction.sol";


contract TestTokenValidatorAuction is TokenValidatorAuction {
    constructor(DepositLocker _depositLocker, IERC20 _token)
        public
        TokenValidatorAuction(100, 14, 50, 123, _depositLocker, _token)
    {}

    function currentPrice() public view returns (uint) {
        return 100;
    }
}
