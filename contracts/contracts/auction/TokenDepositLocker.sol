pragma solidity ^0.5.8;

import "./DepositLocker.sol";
import "../token/TrustlinesNetworkToken.sol";

/*
  The TokenDepositLocker contract locks ERC20 token deposits

  For more information see DepositLocker.sol
*/

contract TokenDepositLocker is DepositLocker {
    // TODO Change to generic ERC token interface
    TrustlinesNetworkToken public token;

    function init(
        uint _releaseTimestamp,
        address _slasher,
        address _depositorsProxy,
        TrustlinesNetworkToken _token
    ) external onlyOwner {
        DepositLocker._init(_releaseTimestamp, _slasher, _depositorsProxy);
        require(
            address(_token) != address(0),
            "Token contract can not be on the zero address!"
        );
        token = _token;
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
