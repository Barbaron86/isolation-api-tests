from collections.abc import Callable, Iterator

import pytest

from tests.clients.http.mock_admin import build_mock_admin_http_test_client
from tests.context.base import DynamicScenarioContext
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema
from tests.tools.cleanup import CleanupManager


@pytest.fixture
def register_gateway_scenario() -> Iterator[
    Callable[[GatewayMockScenarioTestSchema], DynamicScenarioContext]
]:
    """Выдаёт регистрацию динамических сценариев и очищает их после теста.

    Все удаления выполняются до закрытия Admin-клиента. Ошибки удаления
    попадают в отдельный отчёт pytest о teardown.

    Yields:
        Функция, которая регистрирует набор и возвращает контекст для Gateway.
    """
    admin_client = build_mock_admin_http_test_client()
    cleanup = CleanupManager()

    def register(scenario: GatewayMockScenarioTestSchema) -> DynamicScenarioContext:
        scenario_id = admin_client.create_gateway_scenario(scenario)
        cleanup.add(admin_client.delete_scenario, scenario_id, description=f"HTTP mock scenario {scenario_id}")
        return DynamicScenarioContext(scenario=scenario_id)

    with admin_client.client:
        try:
            yield register
        finally:
            cleanup.cleanup()
