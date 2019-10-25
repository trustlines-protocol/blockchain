import logging
from typing import Dict, List, Optional, Set

from eth_typing import Hash32
from eth_utils import from_wei, is_same_address
from web3.datastructures import AttributeDict

from bridge.constants import (
    COMPLETION_EVENT_NAME,
    CONFIRMATION_EVENT_NAME,
    TRANSFER_EVENT_NAME,
    ZERO_ADDRESS,
)
from bridge.events import (
    BalanceCheck,
    ChainRole,
    Event,
    FetcherReachedHeadEvent,
    IsValidatorCheck,
)
from bridge.utils import compute_transfer_hash, sort_events
from bridge.webservice import get_internal_state_summary

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
        self.last_fetcher_reached_head_event: Dict[
            ChainRole, FetcherReachedHeadEvent
        ] = {}

    def log_current_state(self):
        if self.is_validator:
            validator_status = "validating"
        else:
            validator_status = "not validating"

        if self.balance is None:
            balance_str = "-unknown-"
        else:
            balance_str = f"{from_wei(self.balance, 'ether')}"
        logger.info(
            f"reporting internal state\n\n"
            f"===== Internal state ===============================\n"
            f"    {validator_status}, balance {balance_str} coins\n"
            f"    {len(self.transfer_events)} transfer events\n"
            f"    {len(self.scheduled_hashes)} scheduled for confirmation\n"
            f"    {len(self.completion_hashes)} completions seen\n"
            f"====================================================\n"
        )

    @property
    def is_validating(self):
        return self.is_validator and self.is_balance_sufficient

    @property
    def is_balance_sufficient(self):
        return self.balance is not None and self.balance >= self.minimum_balance

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
        sort_events(confirmation_tasks)
        return confirmation_tasks

    def _apply_web3_event(self, event: AttributeDict) -> None:
        event_name = event.event

        if event_name == TRANSFER_EVENT_NAME:
            if event.args.value == 0 or is_same_address(
                event.args["from"], ZERO_ADDRESS
            ):
                logger.warning(f"skipping event {event}")
                return
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

    def _apply_is_validator_check(self, event: IsValidatorCheck):
        if event.is_validator and not self.is_validator:
            logger.info("Account is a member of the validator set")
            self.is_validator = True
        elif not event.is_validator and self.is_validator:
            logger.info("Account is not a member of the validator set")
            self.is_validator = False

    def _apply_balance_check(self, event: BalanceCheck):
        balance_sufficient_before = self.is_balance_sufficient
        self.balance = event.balance
        balance_sufficient_now = self.is_balance_sufficient

        if not balance_sufficient_now:
            logger.warning(
                f"Balance of validator account is only {from_wei(self.balance, 'ether')} TLC."
                f"Transfers will only be confirmed if it is at least "
                f"{from_wei(self.minimum_balance, 'ether')} TLC."
            )

        if not balance_sufficient_before and balance_sufficient_now:
            logger.info(
                f"Validator account balance has increased to "
                f"{from_wei(self.balance, 'ether')} TLC which is above the minimum of "
                f"{from_wei(self.minimum_balance, 'ether')} TLC. Transfers will be confirmed."
            )

    def _apply_fetcher_reached_head_event(self, event: FetcherReachedHeadEvent):
        self.last_fetcher_reached_head_event[event.chain_role] = event

    dispatch_by_event_class = {
        BalanceCheck: _apply_balance_check,
        IsValidatorCheck: _apply_is_validator_check,
        FetcherReachedHeadEvent: _apply_fetcher_reached_head_event,
        AttributeDict: _apply_web3_event,
    }

    def apply_event(self, event):
        assert isinstance(event, Event)
        dispatch = self.dispatch_by_event_class.get(type(event), None)
        if dispatch is None:
            raise ValueError(f"Received unknown event {event}")
        dispatch(self, event)


@get_internal_state_summary.register(TransferRecorder)
def get_state_summary(transfer_recorder):
    return {
        "is_validator": transfer_recorder.is_validator,
        "balance": str(transfer_recorder.balance or -1),
        "num_transfer_events": len(transfer_recorder.transfer_events),
        "num_scheduled_hashes": len(transfer_recorder.scheduled_hashes),
        "num_completions": len(transfer_recorder.completion_hashes),
        "is_validating": transfer_recorder.is_validating,
        "is_balance_sufficient": transfer_recorder.is_balance_sufficient,
        "last_fetcher_reached_head_event": [
            {
                "last_fetched_block_number": x.last_fetched_block_number,
                "chain_role": x.chain_role.value,
                "timestamp": x.timestamp,
            }
            for x in transfer_recorder.last_fetcher_reached_head_event.values()
        ],
    }
