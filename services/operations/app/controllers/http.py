import uuid

from fastapi import HTTPException, status

from services.operations.app.schema.base import (
    GetOperationResponseSchema,
    GetOperationsQuerySchema,
    GetOperationsResponseSchema,
)
from services.operations.app.schema.operation import OperationSchema
from services.operations.services.postgres.repositories.operations import OperationsRepository


async def get_operation(
        operation_id: uuid.UUID,
        operations_repository: OperationsRepository
) -> GetOperationResponseSchema:
    operation = await operations_repository.get_by_id(operation_id)
    if not operation:
        raise HTTPException(
            detail=f"Operation with id {operation_id} not found",
            status_code=status.HTTP_404_NOT_FOUND
        )

    return GetOperationResponseSchema(operation=OperationSchema.model_validate(operation))


async def get_operations(
        query: GetOperationsQuerySchema,
        operations_repository: OperationsRepository
) -> GetOperationsResponseSchema:
    operations = await operations_repository.filter(
        user_id=query.user_id,
        card_id=query.card_id,
        account_id=query.account_id
    )

    return GetOperationsResponseSchema(
        operations=[OperationSchema.model_validate(operation) for operation in operations]
    )
