import uuid
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from tests.context.scenario import Scenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.accounts import GetAccountsResponseTestSchema, GetAccountResponseTestSchema
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/http/data/accounts"),
    logger=get_test_logger("ACCOUNTS_SERVICE_MOCK_LOADER")
)

accounts_mock_router = APIRouter(
    prefix=APITestRoutes.ACCOUNTS,
    tags=[APITestRoutes.ACCOUNTS]
)


@accounts_mock_router.get("", response_model=GetAccountsResponseTestSchema)
async def get_accounts_view(
        user_id: uuid.UUID = Query(alias="userId"),
        scenario: Scenario = Depends(get_scenario_http),
) -> GetAccountsResponseTestSchema:
    """Возвращает счета сценария, принадлежащие запрошенному пользователю.

    Args:
        user_id: Обязательный query-параметр userId.
        scenario: Селектор набора данных из x-test-scenario.

    Returns:
        Счета с совпавшим user_id либо пустой список, если совпадений нет.

    Raises:
        HTTPException: Со статусом 503 в сценарии сбоя списка счетов.
    """
    if scenario == Scenario.ACCOUNTS_LIST_UNAVAILABLE:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE,
        )
    get_accounts_response_data = await loader.load_http(
        file=f"get_accounts/{scenario}.json",
        model=GetAccountsResponseTestSchema
    )
    return GetAccountsResponseTestSchema(
        accounts=[account for account in get_accounts_response_data.accounts if account.user_id == user_id]
    )


@accounts_mock_router.get("/{account_id}", response_model=GetAccountResponseTestSchema)
async def get_account_view(
        account_id: uuid.UUID,
        scenario: Scenario = Depends(get_scenario_http),
) -> GetAccountResponseTestSchema:
    """Возвращает счёт сценария только при совпадении запрошенного ID.

    Args:
        account_id: UUID из пути запроса к Accounts.
        scenario: Селектор набора данных из x-test-scenario.

    Returns:
        Подготовленный счёт выбранного сценария.

    Raises:
        HTTPException: Со статусом 503 в сценарии сбоя деталей счёта либо 404,
            если сценарий не содержит запрошенного ID.
    """
    if scenario == Scenario.ACCOUNT_DETAILS_UNAVAILABLE:
        raise HTTPException(
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
            detail=GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE,
        )
    get_account_response_data = await loader.load_http(
        file=f"get_account/{scenario}.json",
        model=GetAccountResponseTestSchema
    )
    if get_account_response_data.account.id != account_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=account_id),
        )
    return get_account_response_data
