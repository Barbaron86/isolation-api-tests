import uuid
from http import HTTPStatus
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from tests.context.scenario import Scenario
from tests.mock.http.scenario_dependencies import read_dynamic_scenario_header, resolve_scenario
from tests.mock.http.scenarios import DynamicScenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.accounts import GetAccountsResponseTestSchema, GetAccountResponseTestSchema
from tests.schema.mock_gateway import GatewayMockOperation
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/http/data/accounts"),
    logger=get_test_logger("ACCOUNTS_SERVICE_MOCK_LOADER"),
)


def build_accounts_mock_router(*, enable_dynamic_scenarios: bool) -> APIRouter:
    """Подключает список счетов и детали счёта.

    Args:
        enable_dynamic_scenarios: Разрешает выбор набора по ID из Admin API.

    Returns:
        Роутер Accounts для выбранного режима мока.
    """
    router = APIRouter(prefix=APITestRoutes.ACCOUNTS, tags=[APITestRoutes.ACCOUNTS])
    read_scenario = read_dynamic_scenario_header if enable_dynamic_scenarios else get_scenario_http

    @router.get("")
    async def get_accounts_view(
        request: Request,
        user_id: Annotated[uuid.UUID, Query(alias="userId")],
        scenario: Scenario | str | None = Depends(read_scenario),
    ) -> GetAccountsResponseTestSchema:
        """Возвращает счета сценария, принадлежащие запрошенному пользователю.

        Args:
            request: Запрос к HTTP-моку.
            user_id: Идентификатор пользователя из query-параметра userId.
            scenario: Проверенное значение X-Test-Scenario.

        Returns:
            Счета с совпавшим user_id либо пустой список.

        Raises:
            HTTPException: Со статусом 503 в сценарии сбоя списка счетов.
        """
        selected_scenario = await resolve_scenario(request, scenario)
        if isinstance(selected_scenario, DynamicScenario):
            if selected_scenario.is_unavailable(GatewayMockOperation.GET_ACCOUNTS):
                raise HTTPException(
                    HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE
                )
            accounts = selected_scenario.available_accounts
        else:
            if selected_scenario == Scenario.ACCOUNTS_LIST_UNAVAILABLE:
                raise HTTPException(
                    HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE
                )
            response = await loader.load_http(
                file=f"get_accounts/{selected_scenario}.json", model=GetAccountsResponseTestSchema
            )
            accounts = response.accounts
        return GetAccountsResponseTestSchema(accounts=[account for account in accounts if account.user_id == user_id])

    @router.get("/{account_id}", name="get_account_with_dynamic_scenario_view" if enable_dynamic_scenarios else None)
    async def get_account_view(
        request: Request,
        account_id: uuid.UUID,
        scenario: Scenario | str | None = Depends(read_scenario),
    ) -> GetAccountResponseTestSchema:
        """Возвращает счёт выбранного сценария при совпадении его ID.

        Args:
            request: Запрос к HTTP-моку.
            account_id: Идентификатор счёта из пути запроса.
            scenario: Проверенное значение X-Test-Scenario.

        Returns:
            Ответ Accounts с найденным счётом.

        Raises:
            HTTPException: Со статусом 404, если счёта нет в наборе, или 503 при моделируемом сбое.
        """
        selected_scenario = await resolve_scenario(request, scenario)
        if isinstance(selected_scenario, DynamicScenario):
            if selected_scenario.is_unavailable(GatewayMockOperation.GET_ACCOUNT):
                raise HTTPException(
                    HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE
                )
            accounts = selected_scenario.available_accounts
        else:
            if selected_scenario == Scenario.ACCOUNT_DETAILS_UNAVAILABLE:
                raise HTTPException(
                    HTTPStatus.SERVICE_UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE
                )
            response = await loader.load_http(
                file=f"get_account/{selected_scenario}.json", model=GetAccountResponseTestSchema
            )
            accounts = [response.account]
        for account in accounts:
            if account.id == account_id:
                return GetAccountResponseTestSchema(account=account)
        raise HTTPException(
            HTTPStatus.NOT_FOUND, GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=account_id)
        )

    return router
