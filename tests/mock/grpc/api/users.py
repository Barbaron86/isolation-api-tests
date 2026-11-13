from pathlib import Path

from grpc import StatusCode
from grpc.aio import ServicerContext

from contracts.services.users.rpc_get_user_pb2 import GetUserRequest, GetUserResponse
from contracts.services.users.users_service_pb2_grpc import UsersServiceServicer
from tests.context.scenario import Scenario
from tests.mock.grpc.protobuf import to_proto_user
from tests.mock.grpc.tools import resolve_grpc_scenario
from tests.mock.scenarios import DynamicScenario, ScenarioStore
from tests.schema.mock_gateway import GatewayMockOperation
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/grpc/data/users"),
    logger=get_test_logger("USERS_SERVICE_MOCK_LOADER")
)


class UsersMockService(UsersServiceServicer):
    def __init__(self, scenario_store: ScenarioStore | None = None) -> None:
        """Принимает хранилище для динамических ответов GetUser.

        Args:
            scenario_store: Общее хранилище сценариев. При None доступны
                встроенные сценарии.
        """
        self._scenario_store = scenario_store

    async def GetUser(self, request: GetUserRequest, context: ServicerContext) -> GetUserResponse:
        """Возвращает пользователя сценария при совпадении запрошенного ID.

        Args:
            request: Protobuf-запрос с ID пользователя.
            context: Контекст RPC с metadata x-test-scenario.

        Returns:
            Пользователь выбранного сценария.

        Raises:
            grpc.aio.AbortError: С UNAVAILABLE при сбое Users или хранилища,
                NOT_FOUND при отсутствии сценария или пользователя и INVALID_ARGUMENT
                при неверном значении x-test-scenario.
        """
        scenario = await resolve_grpc_scenario(context, self._scenario_store)
        if isinstance(scenario, DynamicScenario):
            if scenario.is_unavailable(GatewayMockOperation.GET_USER):
                await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.USERS_SERVICE_UNAVAILABLE.value)
            for user in scenario.available_users:
                if str(user.id) == request.id:
                    return GetUserResponse(user=to_proto_user(user))
            await context.abort(
                StatusCode.NOT_FOUND,
                GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=request.id),
            )

        if scenario == Scenario.USERS_SERVICE_UNAVAILABLE:
            await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.USERS_SERVICE_UNAVAILABLE.value)
        get_user_response_data = await loader.load_grpc(
            file=f"GetUser/{scenario}.json",
            model=GetUserResponse
        )
        if get_user_response_data.user.id != request.id:
            await context.abort(
                StatusCode.NOT_FOUND,
                GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=request.id),
            )
        return get_user_response_data
