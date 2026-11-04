import uuid
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from tests.context.scenario import Scenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.cards import GetCardResponseTestSchema, GetCardsResponseTestSchema
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/http/data/cards"),
    logger=get_test_logger("CARDS_SERVICE_MOCK_LOADER")
)

cards_mock_router = APIRouter(
    prefix=APITestRoutes.CARDS,
    tags=[APITestRoutes.CARDS]
)


@cards_mock_router.get("", response_model=GetCardsResponseTestSchema)
async def get_cards_view(
        account_id: uuid.UUID = Query(alias="accountId"),
        scenario: Scenario = Depends(get_scenario_http),
) -> GetCardsResponseTestSchema:
    """Возвращает карты сценария, привязанные к запрошенному счёту.

    Args:
        account_id: Обязательный query-параметр accountId.
        scenario: Селектор набора данных из x-test-scenario.

    Returns:
        Карты с совпавшим account_id либо пустой список, если совпадений нет.

    Raises:
        HTTPException: Со статусом 503 в сценарии сбоя Cards.
    """
    if scenario == Scenario.CARDS_SERVICE_UNAVAILABLE:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE,
        )
    get_cards_response_data = await loader.load_http(
        file=f"get_cards/{scenario}.json",
        model=GetCardsResponseTestSchema
    )
    return GetCardsResponseTestSchema(
        cards=[card for card in get_cards_response_data.cards if card.account_id == account_id]
    )


@cards_mock_router.get("/{card_id}", response_model=GetCardResponseTestSchema)
async def get_card_view(
        card_id: uuid.UUID,
        scenario: Scenario = Depends(get_scenario_http),
):
    return await loader.load_http(
        file=f"get_card/{scenario}.json",
        model=GetCardResponseTestSchema
    )
