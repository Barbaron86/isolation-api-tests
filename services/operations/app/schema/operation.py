from datetime import datetime

from pydantic import UUID4

from libs.schema.base import BaseSchema
from services.operations.types.operations import OperationType, OperationStatus


class BaseOperationSchema(BaseSchema):
    type: OperationType
    status: OperationStatus
    amount: float
    user_id: UUID4
    card_id: UUID4
    category: str
    created_at: datetime
    account_id: UUID4


class OperationSchema(BaseOperationSchema):
    id: UUID4


class OperationEventSchema(BaseOperationSchema):
    pass
