import uuid
from datetime import datetime
from typing import Sequence, TypedDict

from libs.postgres.repository import BasePostgresRepository
from services.operations.services.postgres.client import postgres_session_factory
from services.operations.services.postgres.models.operations import OperationsModel
from services.operations.types.operations import OperationType, OperationStatus


class CreateOperationDict(TypedDict):
    type: OperationType
    status: OperationStatus
    amount: float
    user_id: uuid.UUID
    card_id: uuid.UUID
    category: str
    account_id: uuid.UUID
    created_at: datetime


class OperationsRepository(BasePostgresRepository):
    model = OperationsModel

    async def get_by_id(self, operation_id: uuid.UUID) -> OperationsModel | None:
        async with self.session_read() as session:
            return await self.model.get(
                session, clause_filter=(self.model.id == operation_id,)
            )

    async def filter(
            self,
            user_id: uuid.UUID,
            card_id: uuid.UUID | None = None,
            account_id: uuid.UUID | None = None
    ) -> Sequence[OperationsModel]:
        filters = (self.model.user_id == user_id,)
        if card_id:
            filters += (self.model.card_id == card_id,)

        if account_id:
            filters += (self.model.account_id == account_id,)

        async with self.session_read() as session:
            return await self.model.filter(session, clause_filter=filters)

    async def create(self, data: CreateOperationDict) -> OperationsModel:
        async with self.session_write() as session:
            return await self.model.create(session, **data)


def get_operations_repository() -> OperationsRepository:
    return OperationsRepository(session_factory=postgres_session_factory)
