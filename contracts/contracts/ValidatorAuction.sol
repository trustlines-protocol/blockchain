pragma solidity ^0.4.25;

import "./lib/Ownable.sol";


contract ValidatorAuction is Ownable {

    mapping (address => bool) public whitelist;
    mapping (address => uint) public bids;
    address[] public bidders;
    uint public closingPrice;
    AuctionStates public auctionState;

    uint public startTime;
    uint public closeTime;
    uint public auctionDurationInDays;
    uint public startPrice;
    uint public constant NUMBER_OF_PARTICIPANTS = 123;

    event BidSubmitted(address bidder, uint bidValue, uint slotPrice, uint timestamp);
    event AddressWhitelisted(address whitelistedAddress);
    event AuctionStarted(uint startTime);
    event AuctionEnded(uint closeTime, uint closingPrice);
    event AuctionFailed(uint closeTime, uint numberOfBidders);


    enum AuctionStates{
        Deployed,
        Started,
        Ended,
        Failed
    }

    modifier stateIs(AuctionStates state) {
        require(auctionState == state, "Auction is not in the proper state for desired action.");
        _;
    }

    constructor(
        uint _startPriceInEth,
        uint _auctionDurationInDays
    ) {
        require(_auctionDurationInDays > 0, "Duration of auction must be greater than 0");

        auctionDurationInDays = _auctionDurationInDays;
        startPrice = _startPriceInEth * 1 ether;

        auctionState = AuctionStates.Deployed;
    }

    function() external payable stateIs(AuctionStates.Started) {
        bid();
    }

    function bid() public payable stateIs(AuctionStates.Started) {
        assert(now > startTime);
        require(now <= startTime + auctionDurationInDays * 1 days, "Auction has already ended.");
        uint price = currentPrice();
        require(msg.value >= price, "Not enough ether was provided for bidding.");
        require(whitelist[msg.sender], "The sender is not whitelisted.");
        require(! isSenderContract(), "The sender cannot be a contract.");
        require(bidders.length < NUMBER_OF_PARTICIPANTS, "The limit of participants has already been reached.");
        require(bids[msg.sender] == 0, "The sender has already bid.");

        bids[msg.sender] = msg.value;
        bidders.push(msg.sender);

        emit BidSubmitted(msg.sender, msg.value, price, now);

        if (bidders.length == NUMBER_OF_PARTICIPANTS) {
            auctionState = AuctionStates.Ended;
            closeTime = now;
            closingPrice = price;
            emit AuctionEnded(closeTime, closingPrice);
        }
    }

    function startAuction() public onlyOwner stateIs(AuctionStates.Deployed) {
        auctionState = AuctionStates.Started;
        startTime = now;

        emit AuctionStarted(now);
    }

    function closeAuction() public stateIs(AuctionStates.Started) {
        require(now > startTime + auctionDurationInDays * 1 days, "The auction cannot be closed this early.");
        assert(bidders.length < NUMBER_OF_PARTICIPANTS);

        auctionState = AuctionStates.Failed;
        closeTime = now;
        emit AuctionFailed(closeTime, bidders.length);
    }

    function addToWhitelist(address[] addressesToWhitelist) public onlyOwner stateIs(AuctionStates.Deployed) {
        for (uint32 i = 0; i < addressesToWhitelist.length; i++) {
            whitelist[addressesToWhitelist[i]] = true;
            emit AddressWhitelisted(addressesToWhitelist[i]);
        }
    }

    function currentPrice() public view returns (uint) {
        require(now >= startTime, "The current price can only be calculated after the auction started.");
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
        require(auctionState == AuctionStates.Ended || auctionState == AuctionStates.Failed, "You cannot withdraw before the auction is ended or it failed.");
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
