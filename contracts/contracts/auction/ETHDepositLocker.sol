pragma solidity ^0.5.8;

import "./BaseDepositLocker.sol";


/*
  The ETHDepositLocker contract locks ETH deposits

  For more information see DepositLocker.sol
*/

contract ETHDepositLocker is BaseDepositLocker {
    function init(
        uint _releaseTimestamp,
        address _slasher,
        address _depositorsProxy
    ) external onlyOwner {
        BaseDepositLocker._init(_releaseTimestamp, _slasher, _depositorsProxy);
    }

    function _receive(uint amount) internal {
        require(msg.value == amount, "did not receive correct amount");
    }

    function _transfer(address payable recipient, uint amount) internal {
        recipient.transfer(amount);
    }

    function _burn(uint amount) internal {
        address(0).transfer(amount);
    }
}
