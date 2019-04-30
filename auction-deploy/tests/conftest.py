import eth_tester

# increase eth_tester's GAS_LIMIT
# Otherwise we can't whitelist enough addresses for the validator auction in one transaction
assert eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT < 8 * 10 ** 6
eth_tester.backends.pyevm.main.GENESIS_GAS_LIMIT = 8 * 10 ** 6
