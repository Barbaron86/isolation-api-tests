from typing import Self

from fastapi import Query
from pydantic import UUID4

from libs.schema.base import BaseSchema
from libs.schema.query import QuerySchema
from services.accounts.types import AccountType, AccountStatus


class AccountSchema(BaseSchema):
    id: UUID4
    type: AccountType
    status: AccountStatus
    user_id: UUID4
    balance: float


class GetAccountResponseSchema(BaseSchema):
    account: AccountSchema


class GetAccountsQuerySchema(QuerySchema):
    user_id: UUID4

    @classmethod
    async def as_query(cls, user_id: UUID4 = Query(alias="userId")) -> Self:
        return GetAccountsQuerySchema(user_id=user_id)


class GetAccountsResponseSchema(BaseSchema):
    accounts: list[AccountSchema]
