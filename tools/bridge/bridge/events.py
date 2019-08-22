from abc import ABC

import attr
from web3.datastructures import AttributeDict


class Event(ABC):
    pass


# Register AttributeDict as a subclass of Event as it is used to represent contract events in
# web3.py
Event.register(AttributeDict)


class ControlEvent(Event, ABC):
    pass


@attr.s(auto_attribs=True)
class BalanceCheck(ControlEvent):
    balance: int


@attr.s(auto_attribs=True)
class IsValidatorCheck(ControlEvent):
    is_validator: bool
