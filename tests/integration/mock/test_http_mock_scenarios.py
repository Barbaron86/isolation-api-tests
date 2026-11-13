from collections.abc import Iterator
from http import HTTPStatus
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.assertions.base import assert_equal
from tests.assertions.http.base import assert_status_code
from tests.assertions.http.cards import assert_single_card_in_response
from tests.clients.http.mock_admin import SCENARIOS_PATH, MockAdminHTTPTestClient
from tests.mock.http.server import create_app
from tests.schema.cards import GetCardsResponseTestSchema
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema
from tests.tools.gateway_data import make_account, make_card
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason


@pytest.fixture
def mock_http_client() -> Iterator[TestClient]:
    """Открывает клиент HTTP-мока с хранилищем, принадлежащим тесту."""
    with TestClient(create_app(enable_dynamic_scenarios=True)) as client:
        yield client


def test_admin_api_registers_reads_and_deletes_scenario(mock_http_client: TestClient) -> None:
    """Проверяет регистрацию, чтение и повторное удаление сценария.

    Args:
        mock_http_client: Клиент изолированного HTTP-мока.
    """
    card = make_card(account_id=uuid4())
    payload = {"card": card.model_dump(mode="json", by_alias=True)}

    create_scenario_response = mock_http_client.post(SCENARIOS_PATH, json=payload)
    assert_status_code(create_scenario_response.status_code, HTTPStatus.CREATED)
    scenario_id = create_scenario_response.json()["id"]
    assert scenario_id.startswith("dynamic-")
    scenario_path = f"{SCENARIOS_PATH}/{scenario_id}"
    expected_scenario = {"id": scenario_id, **payload}
    assert_equal(create_scenario_response.json(), expected_scenario, "registered scenario")

    get_scenario_response = mock_http_client.get(scenario_path)
    assert_status_code(get_scenario_response.status_code, HTTPStatus.OK)
    assert_equal(get_scenario_response.json(), expected_scenario, "stored scenario")

    delete_scenario_response = mock_http_client.delete(scenario_path)
    assert_status_code(delete_scenario_response.status_code, HTTPStatus.NO_CONTENT)
    repeat_delete_scenario_response = mock_http_client.delete(scenario_path)
    assert_status_code(repeat_delete_scenario_response.status_code, HTTPStatus.NO_CONTENT)

    get_deleted_scenario_response = mock_http_client.get(scenario_path)
    assert_status_code(get_deleted_scenario_response.status_code, HTTPStatus.NOT_FOUND)
    assert_equal(get_deleted_scenario_response.json(), {"detail": f"Scenario {scenario_id} not found"}, "deleted scenario")

    get_deleted_card_response = mock_http_client.get(
        f"{APITestRoutes.CARDS}/{card.id}", headers={"x-test-scenario": scenario_id},
    )
    assert_status_code(get_deleted_card_response.status_code, HTTPStatus.NOT_FOUND)
    assert_equal(get_deleted_card_response.json(), {"detail": f"Scenario {scenario_id} not found"}, "missing scenario")


def test_http_mock_isolates_cards_for_the_same_account_id(mock_http_client: TestClient) -> None:
    """Проверяет выбор набора по заголовку и фильтрацию карт по ID счёта.

    Args:
        mock_http_client: Клиент изолированного HTTP-мока.
    """
    admin_client = MockAdminHTTPTestClient(client=mock_http_client)
    account_id = uuid4()
    first_card = make_card(account_id=account_id)
    second_card = make_card(account_id=account_id)
    other_card = make_card(account_id=uuid4())
    first_scenario_id = admin_client.create_gateway_scenario(
        GatewayMockScenarioTestSchema(cards=[other_card, first_card]),
    )
    second_scenario_id = admin_client.create_gateway_scenario(
        GatewayMockScenarioTestSchema(cards=[second_card]),
    )
    account_query = {"accountId": str(account_id)}

    first_get_cards_response = mock_http_client.get(
        APITestRoutes.CARDS, params=account_query, headers={"x-test-scenario": first_scenario_id},
    )
    assert_status_code(first_get_cards_response.status_code, HTTPStatus.OK)
    assert_single_card_in_response(
        GetCardsResponseTestSchema.model_validate_json(first_get_cards_response.content), first_card,
    )

    second_get_cards_response = mock_http_client.get(
        APITestRoutes.CARDS, params=account_query, headers={"x-test-scenario": second_scenario_id},
    )
    assert_status_code(second_get_cards_response.status_code, HTTPStatus.OK)
    assert_single_card_in_response(
        GetCardsResponseTestSchema.model_validate_json(second_get_cards_response.content), second_card,
    )


def test_http_mock_returns_cards_when_account_is_absent(mock_http_client: TestClient) -> None:
    """Проверяет сценарий, в котором карта зарегистрирована без записи счёта.

    Args:
        mock_http_client: Клиент изолированного HTTP-мока.
    """
    account_id = uuid4()
    card = make_card(account_id=account_id)
    admin_client = MockAdminHTTPTestClient(client=mock_http_client)
    scenario_id = admin_client.create_gateway_scenario(GatewayMockScenarioTestSchema(cards=[card]))
    scenario_headers = {"x-test-scenario": scenario_id}
    expected_detail = GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=account_id)

    get_cards_response = mock_http_client.get(
        APITestRoutes.CARDS, params={"accountId": str(account_id)}, headers=scenario_headers,
    )
    assert_status_code(get_cards_response.status_code, HTTPStatus.OK)
    assert_single_card_in_response(GetCardsResponseTestSchema.model_validate_json(get_cards_response.content), card)

    get_account_response = mock_http_client.get(f"{APITestRoutes.ACCOUNTS}/{account_id}", headers=scenario_headers)
    assert_status_code(get_account_response.status_code, HTTPStatus.NOT_FOUND)
    assert_equal(get_account_response.json(), {"detail": expected_detail}, "missing account error")
