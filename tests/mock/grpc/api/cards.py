from pathlib import Path

from grpc import StatusCode
from grpc.aio import ServicerContext

from contracts.services.cards.cards_service_pb2_grpc import CardsServiceServicer
from contracts.services.cards.rpc_get_card_pb2 import GetCardRequest, GetCardResponse
from contracts.services.cards.rpc_get_cards_pb2 import GetCardsRequest, GetCardsResponse
from tests.context.scenario import Scenario
from tests.mock.grpc.protobuf import to_proto_card
from tests.mock.grpc.tools import get_scenario_grpc, resolve_grpc_scenario
from tests.mock.scenarios import DynamicScenario, ScenarioStore
from tests.schema.mock_gateway import GatewayMockOperation
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/grpc/data/cards"),
    logger=get_test_logger("CARDS_SERVICE_MOCK_LOADER")
)


class CardsMockService(CardsServiceServicer):
    def __init__(self, scenario_store: ScenarioStore | None = None) -> None:
        """Принимает хранилище для динамических ответов GetCards.

        Args:
            scenario_store: Общее хранилище сценариев. При None доступны
                встроенные сценарии.
        """
        self._scenario_store = scenario_store

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
            grpc.aio.AbortError: С UNAVAILABLE при сбое Cards или хранилища,
                NOT_FOUND при отсутствии сценария и INVALID_ARGUMENT при неверном
                значении x-test-scenario.
        """
        scenario = await resolve_grpc_scenario(context, self._scenario_store)
        if isinstance(scenario, DynamicScenario):
            if scenario.is_unavailable(GatewayMockOperation.GET_CARDS):
                await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE.value)
            return GetCardsResponse(
                cards=[
                    to_proto_card(card)
                    for card in scenario.available_cards
                    if str(card.account_id) == request.account_id
                ]
            )

        if scenario == Scenario.CARDS_SERVICE_UNAVAILABLE:
            await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE.value)
        get_cards_response_data = await loader.load_grpc(
            file=f"GetCards/{scenario}.json",
            model=GetCardsResponse
        )
        return GetCardsResponse(
            cards=[card for card in get_cards_response_data.cards if card.account_id == request.account_id]
        )
