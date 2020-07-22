# TLBC Bridge

## Overview

The bridge enables users to exchange TLN tokens for TLC tokens. TLN is a fixed-supply ERC20 token on the Ethereum main chain (sometimes called "foreign chain"), TLC is the native currency ("Ether") on the Trustlines blockchain ("home chain"). The bridge is one way only.

The bridge is operated by a list of validators which coincide with the validators of the chain itself. Each transfer through the bridge must be signed off by at least 50% of the validators to be deemed valid.

Other than via the votes of the validators, there is no communication between the chains.

## Architecture

### Smart Contracts

#### Foreign Chain

On the main chain, there is the `TrustlinesNetworkToken` and the `ForeignBridge` contract. Users are expected to send the tokens they want to transfer to the `ForeignBridge` where they are effectively locked. Anyone can request to burn them to make this official. Validators are expected to listen for `Transfer` events to the `ForeignBridge`.

#### Home Chain

On the home chain, there is the `ValidatorProxy` and the `HomeBridge` contract. The `HomeBridge` is allotted a large amount of TLC at genesis so that it can handle the total supply of TLN. Validators are expected to call `confirmTransfer` for every unconfirmed transfer. Once enough signatures have been collected, the contract will pay out the requested amount to the transfer event's sender address. Only confirmations of accounts which are validators at time of payout count. This is checked by using the `ValidatorProxy` referenced in the contract

### tlbc-bridge

The `tlbc-bridge` is the worker that validators are supposed to run. It connects to two blockchain nodes: One for the home and one for the foreign chain. It listens to events and sends confirmation transactions if necessary. Reorgs longer than a configurable number of blocks on both home and foreign chain are ignored. The watcher is based on gevent and web3.py and consists of the components described in the following.

#### Event Fetchers

For each chain, there's one event fetcher, responsible for pulling relevant Transfer events (foreign) or confirmation as well as completion events (home). Results are put on one queue per chain. To signal the fact that the chain is fully synced, a special kind of event with a timestamp is used.

#### Validator Balance Watcher

The validator balance watcher regularly checks the balance of the configured validator account on the home chain and puts the result on the control queue (so that confirming transfers can be paused if the balance goes too low).

#### Validator Status Watcher

The validator status watcher regularly checks if the configured account is actually a validator or not. If this is not the case, no validation will take place. If a validator leaves the validator set, the program is exited. Results are put on the control queue.

#### Confirmation Task Planner

The confirmation task planner receives both chain event as well as the control queue and decides if a transfer should be confirmed or not. Most logic is outsourced to the transfer recorder instance. Scheduled transfers are put on a queue.

#### Confirmation Sender

The confirmation sender sends a confirmation transaction for each event received from the confirmation task planner via a queue.

#### Confirmation Watcher

The confirmation watcher does nothing but check if sent confirmation transactions have been successful or not.
