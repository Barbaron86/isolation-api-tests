import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from libs.routes import APIRoutes
from services.operations.app.controllers.http import get_operation, get_operations
from services.operations.app.schema.base import (
    GetOperationResponseSchema,
    GetOperationsQuerySchema,
    GetOperationsResponseSchema,
)
from services.operations.services.postgres.repositories.operations import (
    OperationsRepository,
    get_operations_repository
)

operations_router = APIRouter(
    prefix=APIRoutes.OPERATIONS,
    tags=[APIRoutes.OPERATIONS.as_tag()]
)


@operations_router.get('', response_model=GetOperationsResponseSchema)
async def get_operations_view(
        query: Annotated[GetOperationsQuerySchema, Depends(GetOperationsQuerySchema.as_query)],
        operations_repository: Annotated[OperationsRepository, Depends(get_operations_repository)],
):
    return await get_operations(query, operations_repository)


@operations_router.get('/{operation_id}', response_model=GetOperationResponseSchema)
async def get_operation_view(
        operation_id: uuid.UUID,
        operations_repository: Annotated[OperationsRepository, Depends(get_operations_repository)],
):
    return await get_operation(operation_id, operations_repository)
