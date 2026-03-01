from uuid import UUID

import grpc

from contracts.services.operations.operations_service_pb2_grpc import OperationsServiceStub
from tests.clients.grpc.client import GRPCTestClient, build_grpc_test_channel
from tests.tools.logger import get_test_logger
from tests.config import test_settings
from contracts.services.operations.rpc_get_operation_pb2 import GetOperationRequest, GetOperationResponse
from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsRequest, GetOperationsResponse


class OperationsGRPCTestClient(GRPCTestClient):
    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)

        self.stub = OperationsServiceStub(channel)

    def get_operation_api(self, request: GetOperationRequest) -> GetOperationResponse:
        return self.stub.GetOperation(request)

    def get_operations_api(self, request: GetOperationsRequest) -> GetOperationsResponse:
        return self.stub.GetOperations(request)

    def get_operation(self, operation_id: UUID) -> GetOperationResponse:
        request = GetOperationRequest(id=str(operation_id))
        return self.get_operation_api(request)

    def get_operations(
            self,
            user_id: UUID,
            card_id: UUID | None = None,
            account_id: UUID | None = None,
    ) -> GetOperationsResponse:

        request = GetOperationsRequest(user_id=str(user_id))
        if card_id is not None:
            request.card_id = str(card_id)
        if account_id is not None:
            request.account_id = str(account_id)
        return self.get_operations_api(request)


def build_operations_grpc_test_client() -> OperationsGRPCTestClient:
    channel = build_grpc_test_channel(
        logger=get_test_logger("OPERATIONS_GRPC_TEST_CLIENT"),
        config=test_settings.operations_grpc_client
    )
    return OperationsGRPCTestClient(channel=channel)
