from abc import ABC
from enum import Enum

import attr
from web3.datastructures import AttributeDict


class Event(ABC):
    pass


# Register AttributeDict as a subclass of Event as it is used to represent contract events in
# web3.py
Event.register(AttributeDict)


class ChainRole(Enum):
    home = "home"
    foreign = "foreign"

    @property
    def configuration_key(self):
        return f"{self.name}_chain"


@attr.s(auto_attribs=True)
class FetcherReachedHeadEvent(Event):
    timestamp: float
    chain_role: ChainRole
    last_fetched_block_number: int


class ControlEvent(Event, ABC):
    pass


@attr.s(auto_attribs=True)
class BalanceCheck(ControlEvent):
    balance: int


@attr.s(auto_attribs=True)
class IsValidatorCheck(ControlEvent):
    is_validator: bool
