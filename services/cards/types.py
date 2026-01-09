from enum import StrEnum

from libs.base.enums import ProtoEnum


class CardType(ProtoEnum, StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    VIRTUAL = "VIRTUAL"
    PHYSICAL = "PHYSICAL"


class CardStatus(ProtoEnum, StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    ACTIVE = "ACTIVE"
    FROZEN = "FROZEN"
    CLOSED = "CLOSED"
    BLOCKED = "BLOCKED"


class CardPaymentSystem(ProtoEnum, StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    MASTERCARD = "MASTERCARD"
    VISA = "VISA"
