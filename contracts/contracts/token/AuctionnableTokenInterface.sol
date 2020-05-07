pragma solidity ^0.5.8;

contract AuctionnableTokenInterface {
    /**
    * @dev Returns the amount of tokens owned by `account`.
    */
    function balanceOf(address account) public view returns (uint256);

    /**
    * @dev Returns the remaining number of tokens that `spender` will be
    * allowed to spend on behalf of `owner` through {transferFrom}. This is
    * zero by default.
    *
    * This value changes when {approve} or {transferFrom} are called.
    */
    function allowance(address owner, address spender)
        public
        view
        returns (uint256);

    /**
    * @dev Sets `amount` as the allowance of `spender` over the caller's tokens.
    *
    * Returns a boolean value indicating whether the operation succeeded.
    *
    * Approve with a value of `MAX_UINT = 2 ** 256 - 1` will symbolize
    * an approval of infinite value.
    *
    * IMPORTANT:to prevent the risk that someone may use both the old and
    * the new allowance by unfortunate transaction ordering,
    * the approval must be set to 0 before it can be changed to any
    * different desired value.
    *
    * see: https://github.com/ethereum/EIPs/issues/20#issuecomment-263524729
    *
    * Emits an {Approval} event.
    */
    function approve(address spender, uint256 value) public returns (bool);

    /**
    * @dev Moves `amount` tokens from `sender` to `recipient` using the
    * allowance mechanism. `amount` is then deducted from the caller's
    * allowance unless the allowance is `MAX_UINT = 2 ** 256 - 1`.
    *
    * Returns a boolean value indicating whether the operation succeeded.
    *
    * Emits a {Transfer} event.
    */
    function transferFrom(address sender, address recipient, uint256 amount)
        public
        returns (bool);
}

/*
The MIT License (MIT)

Copyright (c) 2016-2019 zOS Global Limited

Permission is hereby granted, free of charge, to any person obtaining
a copy of this software and associated documentation files (the
"Software"), to deal in the Software without restriction, including
without limitation the rights to use, copy, modify, merge, publish,
distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to
the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.
*/
