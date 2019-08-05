import logging
from typing import Any, Dict

import gevent
from eth_keys.datatypes import PrivateKey
from eth_utils import int_to_big_endian, keccak, to_checksum_address
from gevent.queue import Queue
from web3.contract import Contract

from bridge.constants import HOME_CHAIN_STEP_DURATION
from bridge.contract_validation import is_bridge_validator


class ConfirmationSender:
    """Sends confirmTransfer transactions to the home bridge contract."""

    def __init__(
        self,
        transfer_event_queue: Queue,
        home_bridge_contract: Contract,
        private_key: bytes,
        gas_price: int,
        max_reorg_depth: int,
    ):
        self.logger = logging.getLogger("bridge.confirmation_sender.ConfirmationSender")
        self.private_key = private_key
        self.address = PrivateKey(self.private_key).public_key.to_canonical_address()

        if not is_bridge_validator(home_bridge_contract, self.address):
            self.logger.warning(
                f"The address {self.address} is not a bridge validator to confirm "
                f"transfers on the home bridge contract!"
            )

        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_contract = home_bridge_contract
        self.gas_price = gas_price
        self.max_reorg_depth = max_reorg_depth
        self.w3 = self.home_bridge_contract.web3
        self.pending_transaction_queue: Queue[Dict[str, Any]] = Queue()

    def get_next_nonce(self):
        return self.w3.eth.getTransactionCount(self.address, "pending")

    def run(self):
        self.logger.info("Starting")
        try:
            greenlets = [
                gevent.spawn(self.watch_pending_transactions),
                gevent.spawn(self.send_confirmation_transactions),
            ]
            gevent.joinall(greenlets)
        finally:
            for greenlet in greenlets:
                greenlet.kill()

    def send_confirmation_transactions(self):
        while True:
            transfer_event = self.transfer_event_queue.get()

            if not is_bridge_validator(self.home_bridge_contract, self.address):
                self.logger.warning(
                    f"Can not confirm transaction because {to_checksum_address(self.address)}"
                    f"is not a bridge validator!"
                )
                continue

            transaction = self.prepare_confirmation_transaction(transfer_event)

            if transaction is not None:
                self.send_confirmation_transaction(transaction)

    def prepare_confirmation_transaction(self, transfer_event):
        nonce = self.get_next_nonce()
        self.logger.debug(
            f"Preparing confirmation transaction for address "
            f"{transfer_event.args['from']} for {transfer_event.args.value} "
            f"coins (nonce {nonce}, chain {self.w3.eth.chainId})"
        )

        # In case one of the preconditions in the smart contract fails, the buildTransaction
        # function will just fail with a value error and no specific error message.
        # It's currently not possible to get a usable error message from a live parity node
        # without actually sending the transaction.
        # Therefore we just fail with a pretty long error message for the user and hope
        # for the best.
        try:
            # Build the transaction. This might fail when one of the asserts in the smart contract applies
            transaction = self.home_bridge_contract.functions.confirmTransfer(
                self.compute_transfer_hash(transfer_event),
                transfer_event.transactionHash,
                transfer_event.args.value,
                transfer_event.args["from"],
            ).buildTransaction({"gasPrice": self.gas_price, "nonce": nonce})

            # The signing step should not fail, but we want to exit this execution path early,
            # therefore it's inside the try block
            signed_transaction = self.w3.eth.account.sign_transaction(
                transaction, self.private_key
            )

            return signed_transaction
        except ValueError as e:
            # Check if the error is (hopefully) from parity
            if "failed due to an exception" in e.args[0]["message"]:
                self.logger.info(
                    (
                        "Error while building the transaction. This might be because "
                        "you are not in the validator set or the transfer has already "
                        "been confirmed. If this error persists, please check if you "
                        "are a member of the validator set or if your RPC nodes may "
                        "have connection problems: %s"
                    ),
                    e,
                )

                # There is an explicit check for None values before sending. See send_confirmation_transactions
                return None

            # Re-throw all unknown errors
            raise e

    def compute_transfer_hash(self, transfer):
        return keccak(
            b"".join(
                [bytes(transfer.transactionHash), int_to_big_endian(transfer.logIndex)]
            )
        )

    def send_confirmation_transaction(self, transaction):
        self.pending_transaction_queue.put(transaction)
        tx_hash = self.w3.eth.sendRawTransaction(transaction.rawTransaction)
        self.logger.info(f"Sent confirmation transaction {tx_hash.hex()}")
        return tx_hash

    def watch_pending_transactions(self):
        while True:
            self.clear_confirmed_transactions()
            gevent.sleep(HOME_CHAIN_STEP_DURATION)

    def clear_confirmed_transactions(self):
        block_number = self.w3.eth.blockNumber
        confirmation_threshold = block_number - self.max_reorg_depth

        while not self.pending_transaction_queue.empty():
            oldest_pending_transaction = self.pending_transaction_queue.peek()
            receipt = self.w3.eth.getTransactionReceipt(oldest_pending_transaction.hash)
            if receipt and receipt.blockNumber <= confirmation_threshold:
                self.logger.info(
                    f"Transaction has been confirmed: {oldest_pending_transaction.hash.hex()}"
                )
                confirmed_transaction = (
                    self.pending_transaction_queue.get()
                )  # remove from queue
                assert confirmed_transaction == oldest_pending_transaction
            else:
                break  # no need to look at transactions that are even newer
