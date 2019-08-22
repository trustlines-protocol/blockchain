import logging
from typing import Dict, List, Optional, Set

from eth_typing import Hash32
from web3.datastructures import AttributeDict

from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
)
from bridge.control_events import BalanceCheck, ControlEvent, IsValidatorCheck
from bridge.utils import compute_transfer_hash

logger = logging.getLogger(__name__)


class TransferRecorder:
    def __init__(self, minimum_balance: int) -> None:
        self.transfer_events: Dict[Hash32, AttributeDict] = {}

        self.transfer_hashes: Set[Hash32] = set()
        self.confirmation_hashes: Set[Hash32] = set()
        self.completion_hashes: Set[Hash32] = set()

        self.scheduled_hashes: Set[Hash32] = set()

        self.home_chain_synced_until = 0.0

        self.minimum_balance = minimum_balance

        self.is_validator: Optional[bool] = None
        self.balance: Optional[int] = None

    @property
    def is_validating(self):
        return self.is_validator and self.is_balance_sufficient

    @property
    def is_balance_sufficient(self):
        return self.balance is not None and self.balance >= self.minimum_balance

    def apply_proper_event(self, event: AttributeDict) -> None:
        event_name = event.event

        if event_name == TRANSFER_EVENT_NAME:
            transfer_hash = compute_transfer_hash(event)
            self.transfer_hashes.add(transfer_hash)
            self.transfer_events[transfer_hash] = event
        elif event_name == CONFIRMATION_EVENT_NAME:
            transfer_hash = Hash32(bytes(event.args.transferHash))
            assert len(transfer_hash) == 32
            self.confirmation_hashes.add(transfer_hash)
        elif event_name == COMPLETION_EVENT_NAME:
            transfer_hash = Hash32(bytes(event.args.transferHash))
            assert len(transfer_hash) == 32
            self.completion_hashes.add(transfer_hash)
        else:
            raise ValueError(f"Got unknown event {event}")

    def apply_control_event(self, event: ControlEvent) -> None:
        if isinstance(event, IsValidatorCheck):
            if event.is_validator and not self.is_validator:
                logger.info("Account is a member of the validator set")
                self.is_validator = True
            elif not event.is_validator and self.is_validator:
                logger.info("Account is not a member of the validator set")
                self.is_validator = False

        elif isinstance(event, BalanceCheck):
            balance_sufficient_before = self.is_balance_sufficient
            self.balance = event.balance
            balance_sufficient_now = self.is_balance_sufficient

            if balance_sufficient_now and not balance_sufficient_before:
                logger.info("Account balance is sufficiently high")
            elif not balance_sufficient_now and balance_sufficient_before:
                logger.info("Account balance is below safe minimum")

        else:
            raise ValueError(f"Received unknown event {event}")

    def clear_transfers(self) -> None:
        transfer_hashes_to_remove = self.transfer_hashes & self.completion_hashes

        self.transfer_hashes -= transfer_hashes_to_remove
        self.confirmation_hashes -= transfer_hashes_to_remove
        self.completion_hashes -= transfer_hashes_to_remove

        self.scheduled_hashes -= transfer_hashes_to_remove

        for transfer_hash in transfer_hashes_to_remove:
            self.transfer_events.pop(transfer_hash, None)

    def pull_transfers_to_confirm(self) -> List[AttributeDict]:
        if self.is_validating:
            unconfirmed_transfer_hashes = (
                self.transfer_hashes
                - self.confirmation_hashes
                - self.completion_hashes
                - self.scheduled_hashes
            )
            self.scheduled_hashes |= unconfirmed_transfer_hashes
            confirmation_tasks = [
                self.transfer_events[transfer_hash]
                for transfer_hash in unconfirmed_transfer_hashes
            ]
        else:
            confirmation_tasks = []

        self.clear_transfers()
        return confirmation_tasks
