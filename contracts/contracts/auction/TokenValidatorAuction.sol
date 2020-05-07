pragma solidity ^0.5.8;

import "../lib/Ownable.sol";
import "./DepositLocker.sol";
import "../token/AuctionnableTokenInterface.sol";
import "./ValidatorAuction.sol";

contract TokenValidatorAuction is ValidatorAuction {
    AuctionnableTokenInterface public auctionnedToken;

    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _minimalNumberOfParticipants,
        uint _maximalNumberOfParticipants,
        DepositLocker _depositLocker,
        AuctionnableTokenInterface _auctionnedToken
    )
        public
        ValidatorAuction(
            _startPriceInWei,
            _auctionDurationInDays,
            _minimalNumberOfParticipants,
            _maximalNumberOfParticipants,
            _depositLocker
        )
    {
        depositLocker = _depositLocker;
        auctionnedToken = _auctionnedToken;
    }

    function bid() public payable stateIs(AuctionState.Started) {
        require(now > startTime, "It is too early to bid.");
        require(
            now <= startTime + auctionDurationInDays * 1 days,
            "Auction has already ended."
        );

        require(whitelist[msg.sender], "The sender is not whitelisted.");
        require(!isSenderContract(), "The sender cannot be a contract.");
        require(
            bidders.length < maximalNumberOfParticipants,
            "The limit of participants has already been reached."
        );
        require(bids[msg.sender] == 0, "The sender has already bid.");

        uint slotPrice = currentPrice();
        require(
            auctionnedToken.allowance(msg.sender, address(this)) >= slotPrice,
            "The sender did not allow for the auction to withdraw enough tokens"
        );
        require(
            auctionnedToken.balanceOf(msg.sender) >= slotPrice,
            "The sender does not have enough tokens to bid"
        );

        bids[msg.sender] = slotPrice;
        bidders.push(msg.sender);

        lowestSlotPrice = slotPrice;

        depositLocker.registerDepositor(msg.sender);
        emit BidSubmitted(msg.sender, slotPrice, slotPrice, now);

        if (bidders.length == maximalNumberOfParticipants) {
            transitionToDepositPending();
        }

        auctionnedToken.transferFrom(msg.sender, address(this), slotPrice);
    }

}
