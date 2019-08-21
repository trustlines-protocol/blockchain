from abc import ABC

import attr


class ControlEvent(ABC):
    pass


@attr.s(auto_attribs=True)
class BalanceCheck(ControlEvent):
    balance: int


@attr.s(auto_attribs=True)
class IsValidatorCheck(ControlEvent):
    is_validator: bool
