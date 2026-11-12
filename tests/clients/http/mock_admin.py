from http import HTTPStatus

import allure
from httpx import Response
from pydantic import BaseModel

from tests.assertions.http.base import assert_status_code
from tests.clients.http.client import HTTPTestClient, build_http_test_client
from tests.config import test_settings
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema
from tests.tools.logger import get_test_logger


SCENARIOS_PATH = "/__admin/scenarios"


class CreatedScenarioResponseTestSchema(BaseModel):
    """Выделяет из ответа регистрации ID для заголовка и удаления сценария."""

    id: str


class MockAdminHTTPTestClient(HTTPTestClient):
    """Регистрирует и удаляет HTTP-сценарии, которыми владеет тест Gateway."""

    @allure.step("Register HTTP Gateway mock scenario")
    def create_gateway_scenario_api(self, scenario: GatewayMockScenarioTestSchema) -> Response:
        """Отправляет данные зависимостей Gateway в Admin API.

        Args:
            scenario: Записи и ответы зависимостей, подготовленные тестом.

        Returns:
            Сырой ответ регистрации сценария.
        """
        return self.client.post(
            SCENARIOS_PATH, json={"gateway": scenario.model_dump(mode="json", by_alias=True)}
        )

    def create_gateway_scenario(self, scenario: GatewayMockScenarioTestSchema) -> str:
        """Проверяет успешную регистрацию и извлекает ID созданного сценария.

        Args:
            scenario: Записи и ответы зависимостей, отправляемые в Admin API.

        Returns:
            ID сценария, который нужно передать Gateway и удалить после теста.
        """
        response = self.create_gateway_scenario_api(scenario)
        assert_status_code(response.status_code, HTTPStatus.CREATED)
        return CreatedScenarioResponseTestSchema.model_validate_json(response.content).id

    @allure.step("Delete mock scenario {scenario_id}")
    def delete_scenario(self, scenario_id: str) -> None:
        """Удаляет зарегистрированный тестом сценарий и проверяет статус 204.

        Args:
            scenario_id: ID, полученный при регистрации этого сценария.
        """
        response = self.client.delete(f"{SCENARIOS_PATH}/{scenario_id}")
        assert_status_code(response.status_code, HTTPStatus.NO_CONTENT)


def build_mock_admin_http_test_client() -> MockAdminHTTPTestClient:
    """Создаёт Admin API клиент с настройками тестового стенда.

    Returns:
        Клиент, чей HTTPX-транспорт должна закрыть вызывающая фикстура.
    """
    client = build_http_test_client(
        logger=get_test_logger("MOCK_ADMIN_HTTP_TEST_CLIENT"),
        config=test_settings.mock_admin_http_client,
    )
    return MockAdminHTTPTestClient(client=client)
