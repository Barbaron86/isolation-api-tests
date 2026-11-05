from pathlib import Path

from grpc import StatusCode
from grpc.aio import ServicerContext

from contracts.services.cards.cards_service_pb2_grpc import CardsServiceServicer
from contracts.services.cards.rpc_get_card_pb2 import GetCardRequest, GetCardResponse
from contracts.services.cards.rpc_get_cards_pb2 import GetCardsRequest, GetCardsResponse
from tests.context.scenario import Scenario
from tests.mock.grpc.tools import get_scenario_grpc
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/grpc/data/cards"),
    logger=get_test_logger("CARDS_SERVICE_MOCK_LOADER")
)


class CardsMockService(CardsServiceServicer):
    async def GetCard(self, request: GetCardRequest, context: ServicerContext) -> GetCardResponse:
        """Загружает ответ сценария без поиска по ID карты.

        Args:
            request: Protobuf-запрос; ID не используется этим обработчиком.
            context: Контекст RPC с metadata x-test-scenario.

        Returns:
            Ответ GetCard из JSON выбранного сценария.

        Raises:
            FileNotFoundError: Если для GetCard не подготовлен файл сценария.
        """
        scenario = await get_scenario_grpc(context)

        return await loader.load_grpc(
            file=f"GetCard/{scenario}.json",
            model=GetCardResponse
        )

    async def GetCards(self, request: GetCardsRequest, context: ServicerContext) -> GetCardsResponse:
        """Возвращает карты сценария, привязанные к запрошенному счёту.

        Args:
            request: Protobuf-запрос с ID счёта.
            context: Контекст RPC с metadata x-test-scenario.

        Returns:
            Карты с совпавшим account_id либо пустой список без совпадений.

        Raises:
            grpc.aio.AbortError: С UNAVAILABLE в сценарии сбоя Cards.
        """
        scenario = await get_scenario_grpc(context)
        if scenario == Scenario.CARDS_SERVICE_UNAVAILABLE:
            await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE.value)
        get_cards_response_data = await loader.load_grpc(
            file=f"GetCards/{scenario}.json",
            model=GetCardsResponse
        )
        return GetCardsResponse(
            cards=[card for card in get_cards_response_data.cards if card.account_id == request.account_id]
        )
