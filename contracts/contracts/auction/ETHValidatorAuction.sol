pragma solidity ^0.5.8;

import "../lib/Ownable.sol";
import "./DepositLocker.sol";
import "./BaseValidatorAuction.sol";


contract ETHValidatorAuction is BaseValidatorAuction {
    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        DepositLocker _depositLocker
    )
        public
        BaseValidatorAuction(
            _startPriceInWei,
            _auctionDurationInDays,
            _minimalNumberOfParticipants,
            _maximalNumberOfParticipants,
            _depositLocker
        )
    {}

    function() external payable stateIs(AuctionState.Started) {
        bid();
    }

    function _receiveBid(uint amount) internal {
        require(msg.value == amount, "Did not receive correct ETH value");
    }

    function _transfer(address payable recipient, uint amount) internal {
        recipient.transfer(amount);
    }

    function _deposit(uint slotPrice, uint totalValue) internal {
        depositLocker.deposit.value(totalValue)(slotPrice);
    }

    function _getBidAmount(uint slotPrice) internal view returns (uint) {
        require(
            msg.value >= slotPrice,
            "Not enough ether was provided for bidding."
        );
        return msg.value;
    }
}
