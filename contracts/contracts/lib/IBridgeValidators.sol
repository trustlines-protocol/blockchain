pragma solidity 0.5.8;


interface IBridgeValidators {
    function isValidator(address _validator) external view returns(bool);
    function requiredSignatures() external returns(uint256);  // removed `view` from original poa bridge interface
    function owner() external view returns(address);
}
