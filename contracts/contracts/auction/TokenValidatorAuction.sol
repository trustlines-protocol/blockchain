pragma solidity ^0.5.8;

import "../lib/Ownable.sol";
import "./TokenDepositLocker.sol";
import "../token/IERC20.sol";
import "./BaseValidatorAuction.sol";


contract TokenValidatorAuction is BaseValidatorAuction {
    IERC20 public bidToken;

    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        TokenDepositLocker _depositLocker,
        IERC20 _bidToken
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
        bidToken = _bidToken;
    }

    function _receiveBid(uint amount) internal {
        require(msg.value == 0, "Auction does not accept ETH for bidding");
        bidToken.transferFrom(msg.sender, address(this), amount);
    }

    function _transfer(address payable recipient, uint amount) internal {
        bidToken.transfer(recipient, amount);
    }

    function _deposit(uint slotPrice, uint totalValue) internal {
        bidToken.approve(address(depositLocker), totalValue);
        depositLocker.deposit(slotPrice);
    }

    function _getBidAmount(uint slotPrice) internal view returns (uint) {
        return slotPrice;
    }
}
