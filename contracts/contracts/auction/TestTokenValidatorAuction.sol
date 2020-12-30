pragma solidity ^0.8.0;

/*
  The sole purpose of this contract is to be able to test the auction without having to bother with price
*/

import "./TokenValidatorAuction.sol";

contract TestTokenValidatorAuction is TokenValidatorAuction {
    constructor(TokenDepositLocker _depositLocker, IERC20 _token)
        TokenValidatorAuction(100, 14, 50, 123, _depositLocker, _token)
    {}

    function currentPrice() public pure override returns (uint) {
        return 100;
    }
}

// SPDX-License-Identifier: MIT
