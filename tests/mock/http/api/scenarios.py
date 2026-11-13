from http import HTTPStatus
from uuid import uuid4

from fastapi import APIRouter

from tests.mock.http.scenario_dependencies import ScenarioStoreDependency, require_scenario
from tests.mock.scenarios import DynamicScenario, ScenarioPayload


admin_scenarios_router = APIRouter(prefix="/__admin/scenarios", tags=["Mock scenarios"])


@admin_scenarios_router.post("", status_code=HTTPStatus.CREATED, response_model_exclude_none=True)
async def create_scenario(
    payload: ScenarioPayload,
    store: ScenarioStoreDependency,
) -> DynamicScenario:
    """Регистрирует набор данных под новым ID сценария.

    Args:
        payload: Одиночная карта, счёт с картами или набор зависимостей Gateway.
        store: Хранилище сценариев текущего экземпляра мока.

    Returns:
        Сохранённый набор и его ID для заголовка X-Test-Scenario.
    """
    scenario = DynamicScenario(
        id=f"dynamic-{uuid4()}",
        card=payload.card,
        account=payload.account,
        cards=payload.cards,
        gateway=payload.gateway,
    )
    await store.save(scenario)
    return scenario


@admin_scenarios_router.get("/{scenario_id}", response_model_exclude_none=True)
async def get_dynamic_scenario(
    scenario_id: str,
    store: ScenarioStoreDependency,
) -> DynamicScenario:
    """Находит один динамический набор по ID.

    Args:
        scenario_id: Идентификатор, выданный при создании набора.
        store: Хранилище сценариев текущего экземпляра мока.

    Returns:
        Сохранённый набор данных.

    Raises:
        HTTPException: Со статусом 404, если набор отсутствует.
    """
    return await require_scenario(store, scenario_id)


@admin_scenarios_router.delete("/{scenario_id}", status_code=HTTPStatus.NO_CONTENT)
async def delete_scenario(
    scenario_id: str,
    store: ScenarioStoreDependency,
) -> None:
    """Удаляет только указанный сценарий, включая повторный запрос очистки.

    Args:
        scenario_id: Идентификатор набора, который требуется удалить.
        store: Хранилище сценариев текущего экземпляра мока.
    """
    await store.delete(scenario_id)
