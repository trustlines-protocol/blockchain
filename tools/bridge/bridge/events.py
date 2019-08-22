from abc import ABC

import attr


class Event(ABC):
    pass


class ControlEvent(Event, ABC):
    pass


@attr.s(auto_attribs=True)
class BalanceCheck(ControlEvent):
    balance: int


@attr.s(auto_attribs=True)
class IsValidatorCheck(ControlEvent):
    is_validator: bool
