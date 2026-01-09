import uuid

from fastapi import Depends
from httpx import Response, QueryParams, Headers

from config import settings
from libs.context.base import RequestContext
from libs.context.http import get_http_request_context
from libs.http.client.base import HTTPClient, build_http_client
from libs.http.client.handlers import handle_http_error, HTTPClientError
from libs.logger import get_logger
from libs.routes import APIRoutes
from services.accounts.schema import (
    GetAccountResponseSchema,
    GetAccountsQuerySchema,
    GetAccountsResponseSchema
)


class AccountsHTTPClientError(HTTPClientError):
    pass


class AccountsHTTPClient(HTTPClient):
    @handle_http_error(client='AccountsHTTPClient', exception=AccountsHTTPClientError)
    async def get_account_api(self, account_id: uuid.UUID) -> Response:
        return await self.get(f'{APIRoutes.ACCOUNTS}/{account_id}')

    @handle_http_error(client='AccountsHTTPClient', exception=AccountsHTTPClientError)
    async def get_accounts_api(self, query: GetAccountsQuerySchema) -> Response:
        return await self.get(
            APIRoutes.ACCOUNTS,
            params=QueryParams(**query.model_dump(mode='json', by_alias=True))
        )

    async def get_account(self, account_id: uuid.UUID) -> GetAccountResponseSchema:
        response = await self.get_account_api(account_id)
        return GetAccountResponseSchema.model_validate_json(response.text)

    async def get_accounts(self, user_id: uuid.UUID) -> GetAccountsResponseSchema:
        query = GetAccountsQuerySchema(user_id=user_id)
        response = await self.get_accounts_api(query)
        return GetAccountsResponseSchema.model_validate_json(response.text)


def get_accounts_http_client(context: RequestContext = Depends(get_http_request_context)) -> AccountsHTTPClient:
    client = build_http_client(
        logger=get_logger("ACCOUNTS_SERVICE_HTTP_CLIENT"),
        config=settings.accounts_http_client,
        headers=Headers({"x-test-scenario": context.test_scenario})
    )
    return AccountsHTTPClient(client=client)
