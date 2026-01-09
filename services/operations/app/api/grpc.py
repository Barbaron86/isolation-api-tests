from grpc.aio import ServicerContext

from contracts.services.operations.operations_service_pb2_grpc import OperationsServiceServicer
from contracts.services.operations.rpc_get_operation_pb2 import GetOperationRequest, GetOperationResponse
from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsRequest, GetOperationsResponse
from services.operations.app.controllers.grpc import get_operation, get_operations
from services.operations.services.postgres.repositories.operations import get_operations_repository


class OperationsService(OperationsServiceServicer):
    async def GetOperation(self, request: GetOperationRequest, context: ServicerContext) -> GetOperationResponse:
        return await get_operation(
            context=context,
            request=request,
            operations_repository=get_operations_repository()
        )

    async def GetOperations(self, request: GetOperationsRequest, context: ServicerContext) -> GetOperationsResponse:
        return await get_operations(
            request=request,
            operations_repository=get_operations_repository()
        )
