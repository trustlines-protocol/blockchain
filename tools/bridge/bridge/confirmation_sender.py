import logging
from typing import Callable

import gevent
import tenacity
from eth_keys.datatypes import PrivateKey
from eth_utils import is_checksum_address, to_checksum_address
from gevent.queue import Queue
from web3.contract import Contract
from web3.datastructures import AttributeDict
from web3.exceptions import TransactionNotFound

from bridge.constants import (
    CONFIRMATION_TRANSACTION_GAS_LIMIT,
    HOME_CHAIN_STEP_DURATION,
)
from bridge.contract_validation import is_bridge_validator
from bridge.service import Service, run_services
from bridge.utils import compute_transfer_hash

logger = logging.getLogger(__name__)


def make_sanity_check_transfer(foreign_bridge_contract_address):
    """return a function that checks the final transfer right before it is confirmed

    This is the last safety net. We do check that the transfer has
    been sent to the foreign_bridge_contract_address here.
    """
    assert is_checksum_address(foreign_bridge_contract_address)

    def sanity_check_transfer(transfer_event):
        if not isinstance(transfer_event, AttributeDict):
            raise ValueError("not an AttributeDict")
        if transfer_event.args["to"] != foreign_bridge_contract_address:
            raise ValueError("Transfer was not sent to the foreign bridge")

    return sanity_check_transfer


class ConfirmationSender:
    """Sends confirmTransfer transactions to the home bridge contract."""

    def __init__(
        self,
        transfer_event_queue: Queue,
        home_bridge_contract: Contract,
        private_key: bytes,
        gas_price: int,
        max_reorg_depth: int,
        sanity_check_transfer: Callable,
    ):
        self.pending_transaction_queue = Queue()
        w3 = home_bridge_contract.web3

        self.sender = Sender(
            transfer_event_queue=transfer_event_queue,
            home_bridge_contract=home_bridge_contract,
            private_key=private_key,
            gas_price=gas_price,
            max_reorg_depth=max_reorg_depth,
            pending_transaction_queue=self.pending_transaction_queue,
            sanity_check_transfer=sanity_check_transfer,
        )
        self.watcher = Watcher(
            w3=w3,
            pending_transaction_queue=self.pending_transaction_queue,
            max_reorg_depth=max_reorg_depth,
        )
        self.services = [
            Service(
                "watch-pending-transactions", self.watcher.watch_pending_transactions
            ),
            Service(
                "send-confirmation-transactions",
                self.sender.send_confirmation_transactions,
            ),
        ]

    def run(self):
        run_services(self.services)


sender_retry = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
)


class Sender:
    def __init__(
        self,
        *,
        transfer_event_queue: Queue,
        home_bridge_contract: Contract,
        private_key: bytes,
        gas_price: int,
        max_reorg_depth: int,
        pending_transaction_queue: Queue,
        sanity_check_transfer,
    ):
        self.private_key = private_key
        self.address = PrivateKey(self.private_key).public_key.to_canonical_address()

        if not is_bridge_validator(home_bridge_contract, self.address):
            logger.warning(
                f"The address {to_checksum_address(self.address)} is not a bridge validator to confirm "
                f"transfers on the home bridge contract!"
            )

        self.transfer_event_queue = transfer_event_queue
        self.home_bridge_contract = home_bridge_contract
        self.gas_price = gas_price
        self.max_reorg_depth = max_reorg_depth
        self.w3 = self.home_bridge_contract.web3
        self.pending_transaction_queue = pending_transaction_queue
        self.sanity_check_transfer = sanity_check_transfer

    @sender_retry
    def _rpc_send_raw_transaction(self, raw_transaction):
        return self.w3.eth.sendRawTransaction(raw_transaction)

    @sender_retry
    def get_next_nonce(self):
        return self.w3.eth.getTransactionCount(self.address, "pending")

    def send_confirmation_transactions(self):
        while True:
            transfer_event = self.transfer_event_queue.get()

            try:
                self.sanity_check_transfer(transfer_event)
            except Exception as exc:
                raise SystemExit(
                    f"Internal error: sanity check failed for {transfer_event}: {exc}"
                ) from exc
            nonce = self.get_next_nonce()
            transaction = self.prepare_confirmation_transaction(transfer_event, nonce)
            assert transaction is not None
            self.send_confirmation_transaction(transaction)

    def prepare_confirmation_transaction(self, transfer_event, nonce: int):
        transfer_hash = compute_transfer_hash(transfer_event)
        transaction_hash = transfer_event.transactionHash
        amount = transfer_event.args.value
        recipient = transfer_event.args["from"]

        logger.info(
            "confirmTransfer(transferHash=%s transactionHash=%s amount=%s recipient=%s) with nonce=%s",
            transfer_hash.hex(),
            transaction_hash.hex(),
            amount,
            recipient,
            nonce,
        )
        # hard code gas limit to avoid executing the transaction (which would fail as the sender
        # address is not defined before signing the transaction, but the contract asserts that
        # it's a validator)
        transaction = self.home_bridge_contract.functions.confirmTransfer(
            transferHash=transfer_hash,
            transactionHash=transaction_hash,
            amount=amount,
            recipient=recipient,
        ).buildTransaction(
            {
                "gasPrice": self.gas_price,
                "nonce": nonce,
                "gas": CONFIRMATION_TRANSACTION_GAS_LIMIT,
            }
        )

        signed_transaction = self.w3.eth.account.sign_transaction(
            transaction, self.private_key
        )

        return signed_transaction

    def send_confirmation_transaction(self, transaction):
        tx_hash = self._rpc_send_raw_transaction(transaction.rawTransaction)
        self.pending_transaction_queue.put(transaction)
        logger.info(f"Sent confirmation transaction {tx_hash.hex()}")
        return tx_hash


watcher_retry = tenacity.retry(
    wait=tenacity.wait_exponential(multiplier=1, min=5, max=120),
    before_sleep=tenacity.before_sleep_log(logger, logging.WARN),
)


class Watcher:
    def __init__(self, *, w3, pending_transaction_queue: Queue, max_reorg_depth: int):
        self.w3 = w3
        self.max_reorg_depth = max_reorg_depth
        self.pending_transaction_queue = pending_transaction_queue

    def _log_txreceipt(self, receipt):
        if receipt.status == 0:
            logger.warning(f"Transaction failed: {receipt.transactionHash.hex()}")
        else:
            logger.info(f"Transaction confirmed: {receipt.transactionHash.hex()}")

    @watcher_retry
    def _rpc_get_receipt(self, txhash):
        try:
            return self.w3.eth.getTransactionReceipt(txhash)
        except TransactionNotFound:
            return None

    @watcher_retry
    def _rpc_latest_block(self):
        return self.w3.eth.blockNumber

    def _wait_for_next_block(self):
        logger.debug("_wait_for_next_block: %s", HOME_CHAIN_STEP_DURATION)
        gevent.sleep(HOME_CHAIN_STEP_DURATION)

    def watch_pending_transactions(self):
        while True:
            oldest_pending_transaction = self.pending_transaction_queue.get()
            logger.debug(
                "waiting for transaction %s", oldest_pending_transaction.hash.hex()
            )
            receipt = self.wait_for_transaction(oldest_pending_transaction)
            self._log_txreceipt(receipt)

    def wait_for_transaction(self, pending_transaction):
        while True:
            confirmation_threshold = self._rpc_latest_block() - self.max_reorg_depth
            receipt = self._rpc_get_receipt(pending_transaction.hash)
            if receipt and receipt.blockNumber <= confirmation_threshold:
                return receipt
            else:
                self._wait_for_next_block()
