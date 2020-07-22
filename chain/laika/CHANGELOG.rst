==========
Change Log
==========

1.0.0 (2020-03-24)
-------------------------------
- Add fork to new validator set as fixed static JSON array at block number
  `5_652_453`. The set includes 5 new addresses controlled by the Trustlines
  Foundation and Brainbot Technologies. Requires no finality.
- Add a second fork at block `5_652_553` to a validator set as contract with the
  same address list as the fork before. This is based on the restored finality
  by the previous fork.
- Replace boot node list with the new 5 validators enode addresses.
- Increase the minimum required gas price to `1GWei` in the validators node
  configuration.
- Explicitly set the gas target for blocks to `8_000_000` in the node validators
  configuration.
- Limit the transaction queue of validators to `100` transactions per sender.
