pragma solidity ^0.4.25;

import "./lib/Ownable.sol";
import "./DepositLockerInterface.sol";

/*
  The DepositLocker contract locks the deposits for all of the winning
  participants of the auction.

  When the auction is running, the auction contract registers participants that
  have successfully bid with the registerParticipant function. The DepositLocker
  contracts keeps track of the number of participants and also keeps track if a
  participant address can withdraw the deposit.

  All of the participants have to pay the same eth amount when the auction ends.
  The auction contract will deposit the sum of all amounts with a call to
  depositAllBids.

*/


contract DepositLocker is DepositLockerInterface, Ownable {

    bool initialised = false;
    bool bidsDeposited = false;
    address validatorSlasherAddress;
    address auctionContractAddress;
    uint public releaseBlockNumber;

    mapping (address => bool) public canWithdraw;
    uint numberOfParticipants = 0;
    uint closingPrice;
    event ParticipantRegistered(address participantAddress, uint numberOfParticipants);
    event Deposit(uint totalValue, uint closingPrice, uint numberOfParticipants);
    event Withdraw(address withdrawer, uint value);
    event Slash(address validator, uint slashedValue);

    modifier isInitialised() {
        require(initialised, "The contract was not initialised.");
        _;
    }

    modifier isBidsDeposited() {
        require(bidsDeposited, "bids not deposited yet");
        _;
    }

    modifier bidsNotDeposited() {
        require(!bidsDeposited, "bids already deposited");
        _;
    }

    modifier onlyAuctionContract() {
        require(msg.sender == auctionContractAddress, "Only the AuctionContract can call this function.");
        _;
    }

    function() external {}

    function init(uint _releaseBlockNumber, address _validatorSlasherAddress, address _auctionContractAddress)
        external onlyOwner returns (bool _success)
    {
        require(! initialised, "The contract is already initialised.");
        require(_releaseBlockNumber > block.number, "The release block number cannot be lower or equal to the current block number");

        releaseBlockNumber = _releaseBlockNumber;
        validatorSlasherAddress = _validatorSlasherAddress;
        auctionContractAddress = _auctionContractAddress;
        initialised = true;
        owner = address(0);
        return true;
    }

    function registerParticipant(address _participant) public isInitialised bidsNotDeposited onlyAuctionContract returns (bool _success) {
        require(canWithdraw[_participant] == false, "can only register Participant once");
        canWithdraw[_participant] = true;
        numberOfParticipants += 1;
        emit ParticipantRegistered(_participant, numberOfParticipants);
        return true;
    }

    function depositAllBids(uint _closingPrice) public payable isInitialised bidsNotDeposited onlyAuctionContract returns (bool _success) {
        require(numberOfParticipants>0, "no participants");
        require(_closingPrice>0, "_closingPrice must be positive");
        require(msg.value == numberOfParticipants * _closingPrice, "AuctionContract must sent right amount of money");
        closingPrice = _closingPrice;
        bidsDeposited = true;
        emit Deposit(msg.value, closingPrice, numberOfParticipants);
        return true;
    }

    function withdraw() public isInitialised isBidsDeposited returns (bool _success) {
        require(block.number >= releaseBlockNumber, "The deposit cannot be withdrawn yet.");
        require(canWithdraw[msg.sender], "cannot withdraw from sender");

        canWithdraw[msg.sender] = false;
        msg.sender.transfer(closingPrice);
        emit Withdraw(msg.sender, closingPrice);
        return true;
    }

    function slash(address _validator) public isInitialised isBidsDeposited returns (bool _success) {
        require(msg.sender == validatorSlasherAddress, "Only the ValidatorSlasher contract can call this function.");
        require(canWithdraw[_validator], "cannot withdraw from validator");
        canWithdraw[_validator] = false;
        emit Slash(_validator, closingPrice);
        return true;
    }
}
