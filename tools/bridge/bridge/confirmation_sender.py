import logging
from typing import Any, Dict

import gevent
from gevent.queue import Queue

from web3.contract import Contract
from eth_keys.datatypes import PrivateKey
from eth_utils import keccak, int_to_big_endian

from bridge.constants import HOME_CHAIN_STEP_INTERVAL


class ConfirmationSender:
    """Sends confirmTransfer transactions to the home bridge contract."""

    def __init__(
        self,
        transfer_queue: Queue,
        home_bridge_contract: Contract,
        private_key: bytes,
        gas_price: int,
        max_reorg_depth: int,
    ):
        self.transfer_queue = transfer_queue
        self.home_bridge_contract = home_bridge_contract
        self.private_key = private_key
        self.address = PrivateKey(self.private_key).public_key.to_canonical_address()
        self.gas_price = gas_price
        self.max_reorg_depth = max_reorg_depth

        self.w3 = self.home_bridge_contract.web3

        self.logger = logging.getLogger("bridge.confirmation_sender.ConfirmationSender")

        self.pending_transaction_queue: Queue[Dict[str, Any]] = Queue()

    def get_next_nonce(self):
        return self.w3.eth.getTransactionCount(self.address)

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
            transfer = self.transfer_queue.get()
            transaction = self.prepare_confirmation_transaction(transfer)
            self.send_confirmation_transaction(transaction)

    def prepare_confirmation_transaction(self, transfer):
        nonce = self.get_next_nonce()
        transaction = self.home_bridge_contract.functions.confirmTransfer(
            self.compute_transfer_hash(transfer),
            transfer.transactionHash,
            transfer.args.value,
            transfer.args["from"],
        ).buildTransaction({"gasPrice": self.gas_price, "nonce": nonce})
        signed_transaction = self.w3.eth.account.sign_transaction(
            transaction, self.private_key
        )
        return signed_transaction

    def compute_transfer_hash(self, transfer):
        return keccak(
            b"".join(
                [bytes(transfer.transactionHash), int_to_big_endian(transfer.logIndex)]
            )
        )

    def send_confirmation_transaction(self, transaction):
        self.logger.info(f"Sending confirmation transaction {transaction}")
        self.pending_transaction_queue.put(transaction)
        self.w3.eth.sendRawTransaction(transaction.rawTransaction)

    def watch_pending_transactions(self):
        while True:
            self.clear_confirmed_transactions()
            gevent.sleep(HOME_CHAIN_STEP_INTERVAL)

    def clear_confirmed_transactions(self):
        block_number = self.w3.eth.blockNumber
        confirmation_threshold = block_number - self.max_reorg_depth

        while not self.pending_transaction_queue.empty():
            oldest_pending_transaction = self.pending_transaction_queue.peek()
            receipt = self.w3.eth.getTransactionReceipt(oldest_pending_transaction.hash)
            if receipt and receipt.blockNumber <= confirmation_threshold:
                self.logger.info(
                    f"Transaction has been confirmed: {oldest_pending_transaction}"
                )
                confirmed_transaction = (
                    self.pending_transaction_queue.get()
                )  # remove from queue
                assert confirmed_transaction == oldest_pending_transaction
            else:
                break  # no need to look at transactions that are even newer
