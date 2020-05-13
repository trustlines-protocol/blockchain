pragma solidity ^0.5.8;

import "../lib/Ownable.sol";
import "./DepositLocker.sol";
import "../token/IERC20.sol";
import "./ValidatorAuction.sol";


contract TokenValidatorAuction is BaseValidatorAuction {
    IERC20 public auctionnedToken;

    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        DepositLocker _depositLocker,
        IERC20 _auctionnedToken
    )
        public
        BaseValidatorAuction(
            _startPriceInWei,
            _auctionDurationInDays,
            _minimalNumberOfParticipants,
            _maximalNumberOfParticipants,
            _depositLocker
        )
    {
        auctionnedToken = _auctionnedToken;
    }

    function _receiveBid(uint amount) internal {
        require(msg.value == 0, "Auction does not accept ETH for bidding");
        auctionnedToken.transferFrom(msg.sender, address(this), amount);
    }

    function _transfer(address payable recipient, uint amount) internal {
        auctionnedToken.transfer(recipient, amount);
    }

    function _deposit(uint slotPrice, uint totalValue) internal {
        auctionnedToken.approve(address(depositLocker), totalValue);
        depositLocker.deposit(slotPrice);
    }

    function _getBidAmount(uint slotPrice) internal view returns (uint) {
        return slotPrice;
    }
}
