import grpc

from config import settings
from contracts.services.users.rpc_get_user_pb2 import GetUserRequest, GetUserResponse
from contracts.services.users.users_service_pb2_grpc import UsersServiceStub
from libs.context.base import RequestContext
from libs.context.grpc import build_grpc_metadata
from libs.grpc.client.base import GRPCClient, build_grpc_channel
from libs.logger import get_logger


class UsersGRPCClient(GRPCClient):
    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)

        self.stub = UsersServiceStub(channel)

    async def get_user_api(self, request: GetUserRequest, context: RequestContext) -> GetUserResponse:
        return await self.stub.GetUser(request, metadata=build_grpc_metadata(context))

    async def get_user(self, user_id: str, context: RequestContext) -> GetUserResponse:
        request = GetUserRequest(id=user_id)
        return await self.get_user_api(request, context)


def get_users_grpc_client() -> UsersGRPCClient:
    channel = build_grpc_channel(
        logger=get_logger("USERS_SERVICE_GRPC_CLIENT"),
        config=settings.users_grpc_client
    )
    return UsersGRPCClient(channel=channel)
