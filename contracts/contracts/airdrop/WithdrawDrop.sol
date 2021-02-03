pragma solidity ^0.8.0;

import "../token/IERC20.sol";

contract WithdrawDrop {
    mapping(address => uint256) public allowances;
    IERC20 public droppedToken;
    address payable public owner;
    uint256 public timeLimit;

    constructor(
        address[] memory _recipients,
        uint256[] memory _droppedValues,
        address _droppedToken,
        address payable _owner,
        uint256 _timeLimit
    ) {
        require(
            _recipients.length == _droppedValues.length,
            "Number of recipients and dropped values must be equal"
        );
        for (uint16 i = 0; i < _recipients.length; i++) {
            allowances[_recipients[i]] = _droppedValues[i];
        }
        droppedToken = IERC20(_droppedToken);
        timeLimit = _timeLimit;
        owner = _owner;
    }

    function withdraw() public {
        uint256 allowance = allowances[msg.sender];
        require(allowance != 0, "Nothing to withdraw");
        allowances[msg.sender] = 0;
        droppedToken.transfer(msg.sender, allowance);
    }

    function closeDrop() public {
        require(block.timestamp >= timeLimit, "cannot close drop yet");
        droppedToken.transfer(owner, droppedToken.balanceOf(address(this)));
        selfdestruct(owner);
    }
}
