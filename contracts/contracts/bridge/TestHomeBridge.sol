pragma solidity ^0.5.8;

import "./HomeBridge.sol";

contract TestHomeBridge is HomeBridge {

    constructor(ValidatorProxy _proxy) HomeBridge(_proxy) public {
    }

    function() external payable {}
}
