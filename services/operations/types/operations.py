from enum import StrEnum

from libs.base.enums import ProtoEnum


class OperationType(ProtoEnum, StrEnum):
    FEE = "FEE"
    TOP_UP = "TOP_UP"
    PURCHASE = "PURCHASE"
    CASHBACK = "CASHBACK"
    TRANSFER = "TRANSFER"
    REVERSAL = "REVERSAL"
    BILL_PAYMENT = "BILL_PAYMENT"
    CASH_WITHDRAWAL = "CASH_WITHDRAWAL"


class OperationStatus(ProtoEnum, StrEnum):
    FAILED = "FAILED"
    REVERSED = "REVERSED"
    COMPLETED = "COMPLETED"
    IN_PROGRESS = "IN_PROGRESS"
    UNSPECIFIED = "UNSPECIFIED"
