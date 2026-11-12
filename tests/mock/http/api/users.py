import uuid
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from tests.context.scenario import Scenario
from tests.mock.http.scenario_dependencies import read_dynamic_scenario_header, resolve_scenario
from tests.mock.http.scenarios import DynamicScenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.mock_gateway import GatewayMockOperation
from tests.schema.users import GetUserResponseTestSchema
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason


loader = MockLoader(
    root=Path("./tests/mock/http/data/users"),
    logger=get_test_logger("USERS_SERVICE_MOCK_LOADER"),
)


def build_users_mock_router(*, enable_dynamic_scenarios: bool) -> APIRouter:
    """Подключает чтение пользователя для выбранного режима мока.

    Args:
        enable_dynamic_scenarios: Разрешает выбор набора по ID из Admin API.

    Returns:
        Роутер HTTP-мока Users.
    """
    router = APIRouter(prefix=APITestRoutes.USERS, tags=[APITestRoutes.USERS])
    read_scenario = read_dynamic_scenario_header if enable_dynamic_scenarios else get_scenario_http

    @router.get("/{user_id}")
    async def get_user_view(
        request: Request,
        user_id: uuid.UUID,
        scenario: Scenario | str | None = Depends(read_scenario),
    ) -> GetUserResponseTestSchema:
        """Возвращает пользователя выбранного сценария по запрошенному ID.

        Args:
            request: Запрос к HTTP-моку.
            user_id: Идентификатор пользователя из пути запроса.
            scenario: Проверенное значение X-Test-Scenario.

        Returns:
            Ответ Users с найденным пользователем.

        Raises:
            HTTPException: Со статусом 404 при отсутствии пользователя или 503 при сбое.
        """
        selected_scenario = await resolve_scenario(request, scenario)
        if isinstance(selected_scenario, DynamicScenario):
            if selected_scenario.is_unavailable(GatewayMockOperation.GET_USER):
                raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.USERS_SERVICE_UNAVAILABLE)
            users = selected_scenario.available_users
        else:
            if selected_scenario == Scenario.USERS_SERVICE_UNAVAILABLE:
                raise HTTPException(HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.USERS_SERVICE_UNAVAILABLE)
            response = await loader.load_http(
                file=f"get_user/{selected_scenario}.json", model=GetUserResponseTestSchema
            )
            users = [response.user]
        for user in users:
            if user.id == user_id:
                return GetUserResponseTestSchema(user=user)
        raise HTTPException(HTTPStatus.NOT_FOUND, GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=user_id))

    return router
