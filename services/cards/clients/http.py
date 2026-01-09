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
from services.cards.schema import (
    GetCardResponseSchema,
    GetCardsQuerySchema,
    GetCardsResponseSchema
)


class CardsHTTPClientError(HTTPClientError):
    pass


class CardsHTTPClient(HTTPClient):
    @handle_http_error(client='CardsHTTPClient', exception=CardsHTTPClientError)
    async def get_card_api(self, card_id: uuid.UUID) -> Response:
        return await self.get(f'{APIRoutes.CARDS}/{card_id}')

    @handle_http_error(client='CardsHTTPClient', exception=CardsHTTPClientError)
    async def get_cards_api(self, query: GetCardsQuerySchema) -> Response:
        return await self.get(
            APIRoutes.CARDS,
            params=QueryParams(**query.model_dump(mode='json', by_alias=True))
        )

    async def get_card(self, card_id: uuid.UUID) -> GetCardResponseSchema:
        response = await self.get_card_api(card_id)
        return GetCardResponseSchema.model_validate_json(response.text)

    async def get_cards(self, account_id: uuid.UUID) -> GetCardsResponseSchema:
        query = GetCardsQuerySchema(account_id=account_id)
        response = await self.get_cards_api(query)
        return GetCardsResponseSchema.model_validate_json(response.text)


def get_cards_http_client(context: RequestContext = Depends(get_http_request_context)) -> CardsHTTPClient:
    client = build_http_client(
        logger=get_logger("CARDS_SERVICE_HTTP_CLIENT"),
        config=settings.cards_http_client,
        headers=Headers({"x-test-scenario": context.test_scenario})
    )
    return CardsHTTPClient(client=client)
