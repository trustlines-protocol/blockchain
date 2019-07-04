pragma solidity ^0.5.8;


import "./RewardByBlock.sol";


contract TestRewardByBlock is RewardByBlock {

    constructor (address _systemAddress, address _bridgeAddress, uint blockReward) public {
        systemAddress = _systemAddress;

        blockRewardAmount = blockReward;
        homeBridgeAddress = _bridgeAddress;
        initialized = true;
    }

}
