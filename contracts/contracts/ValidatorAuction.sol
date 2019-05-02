pragma solidity ^0.4.25;

import "./lib/Ownable.sol";
import "./DepositLocker.sol";


contract ValidatorAuction is Ownable {

    // Auction constants set on deployment
    uint public auctionDurationInDays;
    uint public startPrice;
    uint public numberOfParticipants;

    AuctionState public auctionState;
    DepositLocker public depositLocker;
    mapping (address => bool) public whitelist;
    mapping (address => uint) public bids;
    address[] public bidders;
    uint public startTime;
    uint public closeTime;
    uint public closingPrice;

    event BidSubmitted(address bidder, uint bidValue, uint slotPrice, uint timestamp);
    event AddressWhitelisted(address whitelistedAddress);
    event AuctionDeployed(uint startPrice, uint auctionDurationInDays, uint numberOfParticipants);
    event AuctionStarted(uint startTime);
    event AuctionEnded(uint closeTime, uint closingPrice);
    event AuctionFailed(uint closeTime, uint numberOfBidders);


    enum AuctionState{
        Deployed,
        Started,
        DepositPending, /* all slots sold, someone needs to call depositBids */
        Ended,
        Failed
    }

    modifier stateIs(AuctionState state) {
        require(auctionState == state, "Auction is not in the proper state for desired action.");
        _;
    }

    constructor(
        uint _startPriceInWei,
        uint _auctionDurationInDays,
        uint _numberOfParticipants,
        DepositLocker _depositLocker
    ) public
    {
        require(_auctionDurationInDays > 0, "Duration of auction must be greater than 0");
        require(_numberOfParticipants > 0, "Number of participants must be greater 0");

        startPrice = _startPriceInWei;
        auctionDurationInDays = _auctionDurationInDays;
        numberOfParticipants = _numberOfParticipants;
        depositLocker = _depositLocker;

        emit AuctionDeployed(startPrice, auctionDurationInDays, numberOfParticipants);
        auctionState = AuctionState.Deployed;
    }

    function() external payable stateIs(AuctionState.Started) {
        bid();
    }

    function bid() public payable stateIs(AuctionState.Started) {
        assert(now > startTime);
        require(now <= startTime + auctionDurationInDays * 1 days, "Auction has already ended.");
        uint price = currentPrice();
        require(msg.value >= price, "Not enough ether was provided for bidding.");
        require(whitelist[msg.sender], "The sender is not whitelisted.");
        require(! isSenderContract(), "The sender cannot be a contract.");
        require(bidders.length < numberOfParticipants, "The limit of participants has already been reached.");
        require(bids[msg.sender] == 0, "The sender has already bid.");

        bids[msg.sender] = msg.value;
        bidders.push(msg.sender);

        depositLocker.registerDepositor(msg.sender);
        emit BidSubmitted(msg.sender, msg.value, price, now);

        if (bidders.length == numberOfParticipants) {
            auctionState = AuctionState.DepositPending;
            closeTime = now;
            closingPrice = price;
            emit AuctionEnded(closeTime, closingPrice);
        }
    }

    function startAuction() public onlyOwner stateIs(AuctionState.Deployed) {
        require(depositLocker.initialized(), "The deposit locker contract is not initialized");

        auctionState = AuctionState.Started;
        startTime = now;

        emit AuctionStarted(now);
    }

    function depositBids() public stateIs(AuctionState.DepositPending) {
        auctionState = AuctionState.Ended;
        depositLocker.deposit.value(closingPrice * numberOfParticipants)(closingPrice);
    }

    function closeAuction() public stateIs(AuctionState.Started) {
        require(now > startTime + auctionDurationInDays * 1 days, "The auction cannot be closed this early.");
        assert(bidders.length < numberOfParticipants);

        auctionState = AuctionState.Failed;
        closeTime = now;
        emit AuctionFailed(closeTime, bidders.length);
    }

    function addToWhitelist(address[] addressesToWhitelist) public onlyOwner stateIs(AuctionState.Deployed) {
        for (uint32 i = 0; i < addressesToWhitelist.length; i++) {
            whitelist[addressesToWhitelist[i]] = true;
            emit AddressWhitelisted(addressesToWhitelist[i]);
        }
    }

    function currentPrice() public view stateIs(AuctionState.Started) returns (uint) {
        assert(now >= startTime);
        uint secondsSinceStart = (now - startTime);
        return priceAtElapsedTime(secondsSinceStart);
    }

    function priceAtElapsedTime(uint secondsSinceStart) public view returns (uint) {
        uint msSinceStart = 1000 * secondsSinceStart;
        uint relativeAuctionTime = msSinceStart / auctionDurationInDays;
        uint decayDivisor = 746571428571;
        uint decay = relativeAuctionTime ** 3 / decayDivisor;
        uint price = startPrice * (1 + relativeAuctionTime)/(1 + relativeAuctionTime + decay);
        return price;
    }

    function withdraw() public {
        require(auctionState == AuctionState.Ended || auctionState == AuctionState.Failed, "You cannot withdraw before the auction is ended or it failed.");
        require(bids[msg.sender] > closingPrice, "The sender has nothing to withdraw.");

        uint valueToWithdraw = bids[msg.sender] - closingPrice;
        assert(valueToWithdraw <= bids[msg.sender]);

        bids[msg.sender] = closingPrice;
        msg.sender.transfer(valueToWithdraw);
    }

    function isSenderContract() internal view returns (bool isContract) {
        uint32 size;
        address sender = msg.sender;
        // solium-disable-next-line security/no-inline-assembly
        assembly {
            size := extcodesize(sender)
        }
        return (size > 0);
    }
}
