import uuid

from grpc import StatusCode
from grpc.aio import ServicerContext

from contracts.services.operations.operation_pb2 import (
    Operation,
    OperationType as ProtoOperationType,
    OperationStatus as ProtoOperationStatus
)
from contracts.services.operations.rpc_get_operation_pb2 import GetOperationRequest, GetOperationResponse
from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsRequest, GetOperationsResponse
from libs.base.date import to_proto_datetime
from services.operations.services.postgres.models import OperationsModel
from services.operations.services.postgres.repositories.operations import OperationsRepository
from services.operations.types.operations import OperationType, OperationStatus

MAP_OPERATION_TYPE_TO_PROTO = OperationType.to_proto_map(ProtoOperationType)
MAP_OPERATION_TYPE_FROM_PROTO = OperationType.from_proto_map(ProtoOperationType)
MAP_OPERATION_STATUS_TO_PROTO = OperationStatus.to_proto_map(ProtoOperationStatus)
MAP_OPERATION_STATUS_FROM_PROTO = OperationStatus.from_proto_map(ProtoOperationStatus)


def build_operation_from_model(model: OperationsModel) -> Operation:
    return Operation(
        id=str(model.id),
        type=MAP_OPERATION_TYPE_TO_PROTO[model.type],
        status=MAP_OPERATION_STATUS_TO_PROTO[model.status],
        amount=model.amount,
        card_id=str(model.card_id),
        user_id=str(model.user_id),
        category=model.category,
        created_at=to_proto_datetime(model.created_at),
        account_id=str(model.account_id)
    )


async def get_operation(
        context: ServicerContext,
        request: GetOperationRequest,
        operations_repository: OperationsRepository
) -> GetOperationResponse:
    operation = await operations_repository.get_by_id(uuid.UUID(request.id))
    if not operation:
        await context.abort(
            code=StatusCode.NOT_FOUND,
            details=f"Operation with id {request.id} not found"
        )

    return GetOperationResponse(operation=build_operation_from_model(operation))


async def get_operations(
        request: GetOperationsRequest,
        operations_repository: OperationsRepository
) -> GetOperationsResponse:
    operations = await operations_repository.filter(
        user_id=uuid.UUID(request.user_id),
        card_id=uuid.UUID(request.card_id) if request.card_id else None,
        account_id=uuid.UUID(request.account_id) if request.account_id else None
    )

    return GetOperationsResponse(
        operations=[build_operation_from_model(operation) for operation in operations]
    )
