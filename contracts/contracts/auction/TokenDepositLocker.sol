pragma solidity ^0.5.8;

import "./DepositLocker.sol";
import "../token/TrustlinesNetworkToken.sol";

/*
  The ETHDepositLocker contract locks ETH deposits

  For more information see DepositLocker.sol
*/

contract TokenDepositLocker is DepositLocker {
    TrustlinesNetworkToken public token;

    constructor(TrustlinesNetworkToken _trustlinesNetworkToken) public {
        require(
            address(_trustlinesNetworkToken) != address(0),
            "Token contract can not be on the zero address!"
        );
        token = _trustlinesNetworkToken;
    }

    function _receive(uint amount) internal {
        require(msg.value == 0, "Token locker contract does not accept ETH");
        // to receive erc20 tokens, we have to pull them
        token.transferFrom(msg.sender, address(this), amount);
    }

    function _transfer(address payable recipient, uint amount) internal {
        token.transfer(recipient, amount);
    }

    function _burn(uint amount) internal {
        token.burn(amount);
    }
}
