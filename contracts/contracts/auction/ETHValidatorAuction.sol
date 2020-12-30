pragma solidity ^0.8.0;

import "../lib/Ownable.sol";
import "./BaseDepositLocker.sol";
import "./BaseValidatorAuction.sol";

contract ETHValidatorAuction is BaseValidatorAuction {
    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        BaseDepositLocker _depositLocker
    )
        BaseValidatorAuction(
            _startPriceInWei,
            _auctionDurationInDays,
            _minimalNumberOfParticipants,
            _maximalNumberOfParticipants,
            _depositLocker
        )
    {}

    function _receiveBid(uint amount) internal override {
        require(msg.value == amount, "Did not receive correct ETH value");
    }

    function _transfer(address payable recipient, uint amount)
        internal
        override
    {
        recipient.transfer(amount);
    }

    function _deposit(uint slotPrice, uint totalValue) internal override {
        depositLocker.deposit{value: totalValue}(slotPrice);
    }

    function _getBidAmount(uint slotPrice)
        internal
        view
        override
        returns (uint)
    {
        require(
            msg.value >= slotPrice,
            "Not enough ether was provided for bidding."
        );
        return msg.value;
    }
}
