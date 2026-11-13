"""Проверки выбора и валидации сценария HTTP-мока."""

import asyncio
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi import FastAPI, HTTPException, Request
from pydantic import ValidationError

from tests.context.scenario import Scenario
from tests.mock.http.scenario_dependencies import resolve_scenario
from tests.mock.scenarios import DynamicScenario, InMemoryScenarioStore, ScenarioPayload
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema
from tests.tools.gateway_data import make_account, make_card, make_user


def test_resolve_builtin_scenario_without_store() -> None:
    """Возвращает имя встроенного сценария без обращения к хранилищу."""
    scenario = Scenario.USER_WITHOUT_ACCOUNTS
    request = Request({"type": "http"})

    assert asyncio.run(resolve_scenario(request, scenario)) is scenario


def test_resolve_dynamic_scenario_by_id() -> None:
    """Возвращает набор из хранилища приложения по ID сценария."""
    scenario = DynamicScenario(id=f"dynamic-{uuid4()}", gateway=GatewayMockScenarioTestSchema())
    app = FastAPI()
    store = InMemoryScenarioStore()
    app.state.scenario_store = store
    request = Request({"type": "http", "app": app})
    asyncio.run(store.save(scenario))

    assert asyncio.run(resolve_scenario(request, scenario.id)) == scenario


def test_resolve_unknown_dynamic_scenario_returns_not_found() -> None:
    """Возвращает 404 с запрошенным ID, если сценарий отсутствует в хранилище."""
    scenario_id = f"dynamic-{uuid4()}"
    app = FastAPI()
    app.state.scenario_store = InMemoryScenarioStore()
    request = Request({"type": "http", "app": app})

    with pytest.raises(HTTPException) as error:
        asyncio.run(resolve_scenario(request, scenario_id))

    assert error.value.status_code == HTTPStatus.NOT_FOUND
    assert error.value.detail == f"Scenario {scenario_id} not found"


def test_resolve_scenario_without_header_returns_bad_request() -> None:
    """Требует имя или ID сценария при отсутствии заголовка."""
    request = Request({"type": "http"})

    with pytest.raises(HTTPException) as error:
        asyncio.run(resolve_scenario(request, None))

    assert error.value.status_code == HTTPStatus.BAD_REQUEST
    assert error.value.detail == "X-Test-Scenario header is required"


@pytest.mark.parametrize("collection", ["users", "accounts", "cards"])
def test_gateway_scenario_rejects_duplicate_ids(collection: str) -> None:
    """Проверяет уникальность ID внутри каждой коллекции сценария Gateway.

    Args:
        collection: Коллекция сущностей с повторяющимся ID.
    """
    user = make_user()
    account = make_account(user_id=user.id)
    card = make_card(account_id=account.id)
    entity = {"users": user, "accounts": account, "cards": card}[collection]

    with pytest.raises(ValidationError, match=f"IDs in {collection} must be unique within a scenario"):
        GatewayMockScenarioTestSchema.model_validate({collection: [entity, entity]})


def test_scenario_payload_rejects_card_for_a_different_account() -> None:
    """Отклоняет набор счёта с картой, принадлежащей другому счёту."""
    account = make_account(user_id=uuid4())
    card = make_card(account_id=uuid4())

    with pytest.raises(ValidationError, match="Each card must belong to the scenario account"):
        ScenarioPayload(account=account, cards=[card])
