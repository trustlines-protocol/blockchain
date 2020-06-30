pragma solidity ^0.5.8;

import "./BaseDepositLocker.sol";
import "../token/IERC20.sol";


/*
  The TokenDepositLocker contract locks ERC20 token deposits

  For more information see DepositLocker.sol
*/

contract TokenDepositLocker is BaseDepositLocker {
    IERC20 public token;

    function init(
        uint _releaseTimestamp,
        address _slasher,
        address _depositorsProxy,
        IERC20 _token
    ) external onlyOwner {
        BaseDepositLocker._init(_releaseTimestamp, _slasher, _depositorsProxy);
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
