import logging
from typing import Any, Dict

import gevent
from gevent.queue import Queue

from web3.contract import Contract
from eth_keys.datatypes import PrivateKey
from eth_utils import keccak, int_to_big_endian

from bridge.constants import HOME_CHAIN_STEP_DURATION


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
        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_contract = home_bridge_contract
        self.private_key = private_key
        self.address = PrivateKey(self.private_key).public_key.to_canonical_address()
        self.gas_price = gas_price
        self.max_reorg_depth = max_reorg_depth

        self.w3 = self.home_bridge_contract.web3

        self.logger = logging.getLogger("bridge.confirmation_sender.ConfirmationSender")

        self.pending_transaction_queue: Queue[Dict[str, Any]] = Queue()

    def get_next_nonce(self):
        try:
            self.nonce = self.nonce + 1
        except AttributeError:
            self.logger.debug(f"Fetching nonce for address {self.address}")
            self.nonce = self.w3.eth.getTransactionCount(self.address)

        return self.nonce

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
            transaction = self.prepare_confirmation_transaction(transfer_event)
            self.send_confirmation_transaction(transaction)

    def prepare_confirmation_transaction(self, transfer_event):
        nonce = self.get_next_nonce()
        self.logger.debug(f"Preparing confirmation transaction for address {transfer_event.args['from']} for {transfer_event.args.value} coins (nonce {nonce})")
        transaction = self.home_bridge_contract.functions.confirmTransfer(
            self.compute_transfer_hash(transfer_event),
            transfer_event.transactionHash,
            transfer_event.args.value,
            transfer_event.args["from"],
        ).buildTransaction({"gasPrice": self.gas_price, "nonce": nonce, "chainId": "0x4874"})
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
        # TODO: Aren't we tracking the transaction hash here?
        self.pending_transaction_queue.put(transaction)
        return self.w3.eth.sendRawTransaction(transaction.rawTransaction)

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
                    f"Transaction has been confirmed: {oldest_pending_transaction}"
                )
                confirmed_transaction = (
                    self.pending_transaction_queue.get()
                )  # remove from queue
                assert confirmed_transaction == oldest_pending_transaction
            else:
                break  # no need to look at transactions that are even newer
