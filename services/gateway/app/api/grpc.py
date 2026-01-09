from grpc.aio import ServicerContext

from contracts.services.gateway.gateway_service_pb2_grpc import GatewayServiceServicer
from contracts.services.gateway.rpc_get_account_details_pb2 import (
    GetAccountDetailsRequest,
    GetAccountDetailsResponse
)
from contracts.services.gateway.rpc_get_user_details_pb2 import (
    GetUserDetailsRequest,
    GetUserDetailsResponse
)
from libs.context.grpc import get_grpc_request_context
from services.accounts.clients.grpc import get_accounts_grpc_client
from services.cards.clients.grpc import get_cards_grpc_client
from services.gateway.app.controllers.grpc import get_user_details, get_account_details
from services.users.clients.grpc import get_users_grpc_client


class GatewayService(GatewayServiceServicer):
    async def GetUserDetails(
            self,
            request: GetUserDetailsRequest,
            context: ServicerContext
    ) -> GetUserDetailsResponse:
        return await get_user_details(
            context=context,
            request=request,
            request_context=get_grpc_request_context(context),
            users_grpc_client=get_users_grpc_client(),
            accounts_grpc_client=get_accounts_grpc_client()
        )

    async def GetAccountDetails(
            self,
            request: GetAccountDetailsRequest,
            context: ServicerContext
    ) -> GetAccountDetailsResponse:
        return await get_account_details(
            context=context,
            request=request,
            request_context=get_grpc_request_context(context),
            cards_grpc_client=get_cards_grpc_client(),
            accounts_grpc_client=get_accounts_grpc_client()
        )
