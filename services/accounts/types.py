from enum import StrEnum

from libs.base.enums import ProtoEnum


class AccountType(ProtoEnum, StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    DEBIT_CARD = "DEBIT_CARD"
    CREDIT_CARD = "CREDIT_CARD"
    DEPOSIT = "DEPOSIT"
    SAVINGS = "SAVINGS"


class AccountStatus(ProtoEnum, StrEnum):
    UNSPECIFIED = "UNSPECIFIED"
    ACTIVE = "ACTIVE"
    PENDING_CLOSURE = "PENDING_CLOSURE"
    CLOSED = "CLOSED"
