pragma solidity ^0.5.8;


interface IRewardByBlock {
    // Produce rewards for the given benefactors, with corresponding reward codes.
    // Only callable by `SYSTEM_ADDRESS`
    function reward(address[] calldata, uint16[] calldata) external returns (address[] memory, uint256[] memory);
}
