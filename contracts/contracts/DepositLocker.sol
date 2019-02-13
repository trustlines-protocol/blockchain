pragma solidity ^0.4.25;

import "./lib/Ownable.sol";
import "./DepositLockerInterface.sol";


contract DepositLocker is DepositLockerInterface, Ownable {

    bool initialised = false;
    address validatorSlasherAddress;
    address auctionContractAddress;
    uint public releaseBlockNumber;
    mapping (address => uint) public deposits;

    event Deposit(address depositOwner, uint value);
    event Withdraw(address withdrawer, uint value);
    event Slash(address validator, uint slashedValue);

    modifier isInitialised() {
        require(initialised, "The contract was not initiated.");
        _;
    }

    function() external {}

    function init(uint _releaseBlockNumber, address _validatorSlasherAddress) external onlyOwner returns (bool _success) {
        require(! initialised, "The contract is already initialised.");
        require(_releaseBlockNumber > block.number, "The release block number cannot be lower or equal to the current block number");

        releaseBlockNumber = _releaseBlockNumber;
        validatorSlasherAddress = _validatorSlasherAddress;

        initialised = true;
        owner = address(0);
        return true;
    }

    function deposit(address _sender) public payable isInitialised returns (bool _success) {
        uint previousDeposit = deposits[_sender];
        deposits[_sender] += msg.value;
        require(previousDeposit <= deposits[_sender], "The value to be deposited overflows when added to the previous deposit.");
        emit Deposit(_sender, msg.value);
        return true;
    }

    function withdraw() public isInitialised returns (bool _success) {
        require(block.number >= releaseBlockNumber, "The deposit cannot be withdrawn yet.");
        uint valueToSend = deposits[msg.sender];
        deposits[msg.sender] = 0;
        msg.sender.transfer(valueToSend);
        emit Withdraw(msg.sender, valueToSend);
        return true;
    }

    function slash(address _validator) public isInitialised returns (bool _success) {
        require(msg.sender == validatorSlasherAddress, "Only the ValidatorSlasher contract can call this function.");
        uint previousDeposit = deposits[_validator];
        deposits[_validator] = 0;
        emit Slash(_validator, previousDeposit);
        return true;
    }
}
