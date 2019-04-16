pragma solidity ^0.4.25;

import "./lib/Ownable.sol";
import "./DepositLockerInterface.sol";

/*
  The DepositLocker contract locks the deposits for all of the winning
  participants of the auction.

  When the auction is running, the auction contract registers participants that
  have successfully bid with the registerDepositor function. The DepositLocker
  contracts keeps track of the number of participants and also keeps track if a
  participant address can withdraw the deposit.

  All of the participants have to pay the same eth amount when the auction ends.
  The auction contract will deposit the sum of all amounts with a call to
  deposit.

*/


contract DepositLocker is DepositLockerInterface, Ownable {

    bool initialised = false;
    bool deposited = false;

    /* We do maintain two special addresses:
       - the slasher, that is allowed to call the slash function
       - the depositorsProxy that registers depositors and deposits a value for
         all of the registered depositors with the deposit function. In our case
         this will be the auction contract.
    */

    address slasher;
    address depositorsProxy;
    uint public releaseBlockNumber;

    mapping (address => bool) public canWithdraw;
    uint numberOfDepositors = 0;
    uint valuePerDepositor;
    event DepositorRegistered(address depositorAddress, uint numberOfDepositors);
    event Deposit(uint totalValue, uint valuePerDepositor, uint numberOfDepositors);
    event Withdraw(address withdrawer, uint value);
    event Slash(address slashedDepositor, uint slashedValue);

    modifier isInitialised() {
        require(initialised, "The contract was not initialised.");
        _;
    }

    modifier isDeposited() {
        require(deposited, "no deposits yet");
        _;
    }

    modifier isNotDeposited() {
        require(!deposited, "already deposited");
        _;
    }

    modifier onlyDepositorsProxy() {
        require(msg.sender == depositorsProxy, "Only the depositorsProxy can call this function.");
        _;
    }

    function() external {}

    function init(uint _releaseBlockNumber, address _slasher, address _depositorsProxy)
        external onlyOwner returns (bool _success)
    {
        require(! initialised, "The contract is already initialised.");
        require(_releaseBlockNumber > block.number, "The release block number cannot be lower or equal to the current block number");

        releaseBlockNumber = _releaseBlockNumber;
        slasher = _slasher;
        depositorsProxy = _depositorsProxy;
        initialised = true;
        owner = address(0);
        return true;
    }

    function registerDepositor(address _depositor) public isInitialised isNotDeposited onlyDepositorsProxy returns (bool _success) {
        require(canWithdraw[_depositor] == false, "can only register Depositor once");
        canWithdraw[_depositor] = true;
        numberOfDepositors += 1;
        emit DepositorRegistered(_depositor, numberOfDepositors);
        return true;
    }

    function deposit(uint _valuePerDepositor) public payable isInitialised isNotDeposited onlyDepositorsProxy returns (bool _success) {
        require(numberOfDepositors>0, "no depositors");
        require(_valuePerDepositor>0, "_valuePerDepositor must be positive");
        require(msg.value == numberOfDepositors * _valuePerDepositor, "the deposit does not match the required value");
        valuePerDepositor = _valuePerDepositor;
        deposited = true;
        emit Deposit(msg.value, valuePerDepositor, numberOfDepositors);
        return true;
    }

    function withdraw() public isInitialised isDeposited returns (bool _success) {
        require(block.number >= releaseBlockNumber, "The deposit cannot be withdrawn yet.");
        require(canWithdraw[msg.sender], "cannot withdraw from sender");

        canWithdraw[msg.sender] = false;
        msg.sender.transfer(valuePerDepositor);
        emit Withdraw(msg.sender, valuePerDepositor);
        return true;
    }

    function slash(address _depositorToBeSlashed) public isInitialised isDeposited returns (bool _success) {
        require(msg.sender == slasher, "Only the slasher can call this function.");
        require(canWithdraw[_depositorToBeSlashed], "cannot slash address");
        canWithdraw[_depositorToBeSlashed] = false;
        emit Slash(_depositorToBeSlashed, valuePerDepositor);
        return true;
    }
}