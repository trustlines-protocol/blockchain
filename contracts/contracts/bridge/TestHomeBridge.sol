pragma solidity ^0.5.8;

import "./HomeBridge.sol";

contract TestHomeBridge is HomeBridge {
    constructor(ValidatorProxy _proxy, uint _validatorsRequiredPercent)
        public
        HomeBridge(_proxy, _validatorsRequiredPercent)
    {}

    function() external payable {}
}
