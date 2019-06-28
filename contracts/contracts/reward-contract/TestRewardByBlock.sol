pragma solidity ^0.5.8;


import "./RewardByBlock.sol";


contract TestRewardByBlock is RewardByBlock {

    constructor (address _systemAddress, address _bridgeAddress) public {
        systemAddress = _systemAddress;
        bridgeAddress = _bridgeAddress;
    }

}
