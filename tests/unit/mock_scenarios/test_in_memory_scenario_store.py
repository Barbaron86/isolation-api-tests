import asyncio
from uuid import uuid4

from tests.mock.http.scenarios import DynamicScenario, InMemoryScenarioStore
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema


def test_in_memory_store_isolates_scenarios_and_store_instances() -> None:
    """Проверяет изоляцию сценариев и повторное удаление одного из них."""
    first = DynamicScenario(id=f"dynamic-{uuid4()}", gateway=GatewayMockScenarioTestSchema())
    second = DynamicScenario(id=f"dynamic-{uuid4()}", gateway=GatewayMockScenarioTestSchema())

    async def check_store() -> None:
        store = InMemoryScenarioStore()
        other_store = InMemoryScenarioStore()
        await store.save(first)
        await store.save(second)

        assert await store.get(first.id) == first
        assert await other_store.get(first.id) is None

        await store.delete(first.id)
        await store.delete(first.id)

        assert await store.get(first.id) is None
        assert await store.get(second.id) == second

    asyncio.run(check_store())
