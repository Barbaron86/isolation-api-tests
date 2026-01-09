import uuid

from fastapi import Depends
from httpx import Response, Headers

from config import settings
from libs.context.base import RequestContext
from libs.context.http import get_http_request_context
from libs.http.client.base import HTTPClient, build_http_client
from libs.http.client.handlers import handle_http_error, HTTPClientError
from libs.logger import get_logger
from libs.routes import APIRoutes
from services.users.schema import GetUserResponseSchema


class UsersHTTPClientError(HTTPClientError):
    pass


class UsersHTTPClient(HTTPClient):
    @handle_http_error(client='UsersHTTPClient', exception=UsersHTTPClientError)
    async def get_user_api(self, user_id: uuid.UUID) -> Response:
        return await self.get(f'{APIRoutes.USERS}/{user_id}')

    async def get_user(self, user_id: uuid.UUID) -> GetUserResponseSchema:
        response = await self.get_user_api(user_id)
        return GetUserResponseSchema.model_validate_json(response.text)


def get_users_http_client(context: RequestContext = Depends(get_http_request_context)) -> UsersHTTPClient:
    client = build_http_client(
        logger=get_logger("USERS_SERVICE_HTTP_CLIENT"),
        config=settings.users_http_client,
        headers=Headers({"x-test-scenario": context.test_scenario})
    )
    return UsersHTTPClient(client=client)
