pragma solidity ^0.8.0;

import "../token/TrustlinesNetworkToken.sol";

contract ForeignBridge {
    uint public requiredBlockConfirmations = 8;
    TrustlinesNetworkToken public trustlinesNetworkToken;

    constructor(TrustlinesNetworkToken _trustlinesNetworkToken) {
        require(
            address(_trustlinesNetworkToken) != address(0),
            "Token contract can not be on the zero address!"
        );

        trustlinesNetworkToken = _trustlinesNetworkToken;
    }

    function burn() public {
        uint256 balance = trustlinesNetworkToken.balanceOf(address(this));
        trustlinesNetworkToken.burn(balance);
    }
}
