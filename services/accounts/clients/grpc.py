import grpc

from config import settings
from contracts.services.accounts.accounts_service_pb2_grpc import AccountsServiceStub
from contracts.services.accounts.rpc_get_account_pb2 import GetAccountRequest, GetAccountResponse
from contracts.services.accounts.rpc_get_accounts_pb2 import GetAccountsRequest, GetAccountsResponse
from libs.context.base import RequestContext
from libs.context.grpc import build_grpc_metadata
from libs.grpc.client.base import GRPCClient, build_grpc_channel
from libs.logger import get_logger


class AccountsGRPCClient(GRPCClient):
    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)

        self.stub = AccountsServiceStub(channel)

    async def get_account_api(self, request: GetAccountRequest, context: RequestContext) -> GetAccountResponse:
        return await self.stub.GetAccount(request, metadata=build_grpc_metadata(context))

    async def get_accounts_api(self, request: GetAccountsRequest, context: RequestContext) -> GetAccountsResponse:
        return await self.stub.GetAccounts(request, metadata=build_grpc_metadata(context))

    async def get_account(self, account_id: str, context: RequestContext) -> GetAccountResponse:
        request = GetAccountRequest(id=account_id)
        return await self.get_account_api(request, context)

    async def get_accounts(self, user_id: str, context: RequestContext) -> GetAccountsResponse:
        request = GetAccountsRequest(user_id=user_id)
        return await self.get_accounts_api(request, context)


def get_accounts_grpc_client() -> AccountsGRPCClient:
    channel = build_grpc_channel(
        logger=get_logger("ACCOUNTS_SERVICE_GRPC_CLIENT"),
        config=settings.accounts_grpc_client
    )
    return AccountsGRPCClient(channel=channel)
