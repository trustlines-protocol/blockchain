pragma solidity ^0.5.8;

import "../token/TrustlinesNetworkToken.sol";


contract ForeignBridge {

    uint public requiredBlockConfirmations = 8;
    TrustlinesNetworkToken public trustlinesNetworkToken;

    constructor(TrustlinesNetworkToken _trustlinesNetworkToken) public {
        trustlinesNetworkToken = _trustlinesNetworkToken;
    }

    function burn() public {
        uint256 balance = trustlinesNetworkToken.balanceOf(address(this));
        trustlinesNetworkToken.burn(balance);
    }
}
