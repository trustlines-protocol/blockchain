contract TestNonPayableRecipient {
    function() external payable {
        require(false, "do not pay me");
    }
}
