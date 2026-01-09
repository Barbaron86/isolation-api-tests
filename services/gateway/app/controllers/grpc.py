from grpc.aio import AioRpcError, ServicerContext

from contracts.services.gateway.account_details_pb2 import AccountDetails
from contracts.services.gateway.rpc_get_account_details_pb2 import (
    GetAccountDetailsRequest,
    GetAccountDetailsResponse
)
from contracts.services.gateway.rpc_get_user_details_pb2 import (
    GetUserDetailsRequest,
    GetUserDetailsResponse
)
from contracts.services.gateway.user_details_pb2 import UserDetails
from libs.context.base import RequestContext
from services.accounts.clients.grpc import AccountsGRPCClient
from services.cards.clients.grpc import CardsGRPCClient
from services.users.clients.grpc import UsersGRPCClient


async def get_user_details(
        context: ServicerContext,
        request: GetUserDetailsRequest,
        request_context: RequestContext,
        users_grpc_client: UsersGRPCClient,
        accounts_grpc_client: AccountsGRPCClient
) -> GetUserDetailsResponse:
    try:
        get_user_response = await users_grpc_client.get_user(
            user_id=request.id,
            context=request_context
        )
    except AioRpcError as error:
        await context.abort(
            code=error.code(),
            details=f"Get user details: {error.details()}"
        )

    try:
        get_accounts_response = await accounts_grpc_client.get_accounts(
            user_id=request.id,
            context=request_context
        )
    except AioRpcError as error:
        await context.abort(
            code=error.code(),
            details=f"Get user details: {error.details()}"
        )

    return GetUserDetailsResponse(
        details=UserDetails(
            user=get_user_response.user,
            accounts=get_accounts_response.accounts
        )
    )


async def get_account_details(
        context: ServicerContext,
        request: GetAccountDetailsRequest,
        request_context: RequestContext,
        cards_grpc_client: CardsGRPCClient,
        accounts_grpc_client: AccountsGRPCClient
) -> GetAccountDetailsResponse:
    try:
        get_cards_response = await cards_grpc_client.get_cards(
            account_id=request.id,
            context=request_context
        )
    except AioRpcError as error:
        await context.abort(
            code=error.code(),
            details=f"Get account details: {error.details()}"
        )

    try:
        get_accounts_response = await accounts_grpc_client.get_account(
            account_id=request.id,
            context=request_context
        )
    except AioRpcError as error:
        await context.abort(
            code=error.code(),
            details=f"Get account details: {error.details()}"
        )

    return GetAccountDetailsResponse(
        details=AccountDetails(
            cards=get_cards_response.cards,
            account=get_accounts_response.account
        )
    )
