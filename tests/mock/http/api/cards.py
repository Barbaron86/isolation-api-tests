import uuid
from http import HTTPStatus
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from tests.context.scenario import Scenario
from tests.mock.http.scenario_dependencies import read_dynamic_scenario_header, resolve_scenario
from tests.mock.scenarios import DynamicScenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.cards import CardTestSchema, GetCardResponseTestSchema, GetCardsResponseTestSchema
from tests.schema.mock_gateway import GatewayMockOperation
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/http/data/cards"),
    logger=get_test_logger("CARDS_SERVICE_MOCK_LOADER"),
)


async def _load_scenario_cards(scenario: Scenario | DynamicScenario) -> list[CardTestSchema]:
    """Получает карты из выбранного сценария.

    Args:
        scenario: Имя встроенного сценария или уже загруженный динамический набор.

    Returns:
        Карты из общего JSON или из динамического набора.

    Raises:
        HTTPException: При моделируемом сбое Cards во встроенном сценарии.
    """
    if isinstance(scenario, DynamicScenario):
        return scenario.available_cards

    if scenario == Scenario.CARDS_SERVICE_UNAVAILABLE:
        raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE)

    response = await loader.load_http(
        file=f"get_cards/{scenario}.json", model=GetCardsResponseTestSchema
    )
    return response.cards


def build_cards_mock_router(*, enable_dynamic_scenarios: bool) -> APIRouter:
    """Подключает маршруты Cards с разбором заголовка для выбранного режима.

    Args:
        enable_dynamic_scenarios: Принимает также ID, выданные Admin API.

    Returns:
        Роутер списка карт и получения одной карты по ID.
    """
    router = APIRouter(prefix=APITestRoutes.CARDS, tags=[APITestRoutes.CARDS])
    read_scenario = read_dynamic_scenario_header if enable_dynamic_scenarios else get_scenario_http

    @router.get("", name="get_cards_with_dynamic_scenario_view" if enable_dynamic_scenarios else None)
    async def get_cards_view(
        request: Request,
        account_id: Annotated[uuid.UUID, Query(alias="accountId")],
        scenario: Scenario | str | None = Depends(read_scenario),
    ) -> GetCardsResponseTestSchema:
        """Возвращает карты выбранного сценария, привязанные к счёту.

        Args:
            request: Запрос к HTTP-моку.
            account_id: Идентификатор счёта из query-параметра accountId.
            scenario: Проверенное значение X-Test-Scenario.

        Returns:
            Список карт счёта, в том числе пустой.

        Raises:
            HTTPException: Со статусом 503 при настроенном сбое списка карт.
        """
        selected_scenario = await resolve_scenario(request, scenario)
        if isinstance(selected_scenario, DynamicScenario) and selected_scenario.is_unavailable(GatewayMockOperation.GET_CARDS):
            raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE)
        cards = await _load_scenario_cards(selected_scenario)
        return GetCardsResponseTestSchema(cards=[card for card in cards if card.account_id == account_id])

    @router.get("/{card_id}", name="get_card_with_dynamic_scenario_view" if enable_dynamic_scenarios else None)
    async def get_card_view(
        request: Request,
        card_id: uuid.UUID,
        scenario: Scenario | str | None = Depends(read_scenario),
    ) -> GetCardResponseTestSchema:
        """Возвращает карту из выбранного сценария по её ID.

        Args:
            request: Запрос к HTTP-моку.
            card_id: Идентификатор карты из пути запроса.
            scenario: Проверенное значение X-Test-Scenario.

        Returns:
            Ответ Cards с найденной картой.

        Raises:
            HTTPException: Со статусом 404, если карты нет в наборе.
        """
        selected_scenario = await resolve_scenario(request, scenario)
        cards = await _load_scenario_cards(selected_scenario)
        for card in cards:
            if card.id == card_id:
                return GetCardResponseTestSchema(card=card)
        raise HTTPException(HTTPStatus.NOT_FOUND, GatewayTestErrorReason.CARD_NOT_FOUND.format(card_id=card_id))

    return router
