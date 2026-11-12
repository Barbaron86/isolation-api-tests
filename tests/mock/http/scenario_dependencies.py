from http import HTTPStatus
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from pydantic import StringConstraints

from tests.context.scenario import Scenario
from tests.mock.http.scenarios import DynamicScenario, ScenarioStore
from tests.mock.http.tools import get_scenario_http


DynamicScenarioId = Annotated[str, StringConstraints(pattern=r"^dynamic-")]
ScenarioHeader = Annotated[Scenario | DynamicScenarioId | None, Header(alias="X-Test-Scenario")]


def read_dynamic_scenario_header(scenario: ScenarioHeader = None) -> Scenario | str | None:
    """Разбирает имя встроенного сценария или динамический ID из заголовка.

    Args:
        scenario: Значение X-Test-Scenario, проверенное FastAPI.

    Returns:
        Имя, динамический ID или None при отсутствии заголовка.
    """
    return scenario


def get_scenario_store(request: Request) -> ScenarioStore:
    """Возвращает хранилище экземпляра мока, который принял запрос.

    Args:
        request: Запрос к моку с включёнными динамическими сценариями.

    Returns:
        Хранилище Admin API и маршрутов Users, Accounts и Cards.
    """
    return request.app.state.scenario_store


ScenarioStoreDependency = Annotated[ScenarioStore, Depends(get_scenario_store)]


async def require_scenario(store: ScenarioStore, scenario_id: str) -> DynamicScenario:
    """Читает зарегистрированный сценарий или возвращает HTTP 404.

    Args:
        store: Хранилище текущего экземпляра мока.
        scenario_id: ID, выданный при регистрации набора.

    Returns:
        Сохранённый сценарий.

    Raises:
        HTTPException: Если в хранилище нет сценария с таким ID.
    """
    scenario = await store.get(scenario_id)
    if scenario is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Scenario {scenario_id} not found")
    return scenario


async def resolve_scenario(request: Request, scenario: Scenario | str | None) -> Scenario | DynamicScenario:
    """Определяет набор данных после проверки параметров HTTP-запроса.

    Args:
        request: Запрос, из которого можно получить хранилище мока.
        scenario: Значение заголовка после разбора FastAPI.

    Returns:
        Имя встроенного сценария для чтения JSON или сохранённый набор данных.

    Raises:
        HTTPException: Если заголовок отсутствует или динамический ID неизвестен.
    """
    if scenario is None or isinstance(scenario, Scenario):
        return get_scenario_http(scenario)
    return await require_scenario(get_scenario_store(request), scenario)
