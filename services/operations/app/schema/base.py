from typing import Self

from fastapi import Query
from pydantic import UUID4

from libs.schema.base import BaseSchema
from libs.schema.query import QuerySchema
from services.operations.app.schema.operation import OperationSchema


class GetOperationResponseSchema(BaseSchema):
    operation: OperationSchema


class GetOperationsQuerySchema(QuerySchema):
    user_id: UUID4
    card_id: UUID4 | None = None
    account_id: UUID4 | None = None

    @classmethod
    def as_query(
            cls,
            user_id: UUID4 = Query(alias="userId"),
            card_id: UUID4 | None = Query(alias="cardId", default=None),
            account_id: UUID4 | None = Query(alias="accountId", default=None)
    ) -> Self:
        return GetOperationsQuerySchema(
            user_id=user_id,
            card_id=card_id,
            account_id=account_id
        )


class GetOperationsResponseSchema(BaseSchema):
    operations: list[OperationSchema]
