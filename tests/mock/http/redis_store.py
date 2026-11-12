from redis.asyncio import Redis

from tests.mock.http.scenarios import DynamicScenario


SCENARIO_KEY_PREFIX = "http-mock:scenarios:"
SCENARIO_TTL_SECONDS = 3600


class RedisScenarioStore:
    """Хранит динамические сценарии в общей для HTTP-воркеров базе Redis."""

    def __init__(self, client: Redis) -> None:
        """Принимает клиент, открытый на время жизни приложения.

        Args:
            client: Асинхронный Redis-клиент текущего HTTP-воркера.
        """
        self._client = client

    async def save(self, scenario: DynamicScenario) -> None:
        """Записывает сценарий и срок хранения одной командой Redis.

        Args:
            scenario: Данные, зарегистрированные через Admin API.
        """
        await self._client.set(
            f"{SCENARIO_KEY_PREFIX}{scenario.id}",
            scenario.model_dump_json(exclude_none=True),
            ex=SCENARIO_TTL_SECONDS,
        )

    async def get(self, scenario_id: str) -> DynamicScenario | None:
        """Читает сохранённый JSON и восстанавливает модель сценария.

        Args:
            scenario_id: Идентификатор, переданный в запросе.

        Returns:
            Сценарий или None, если ключ отсутствует либо истёк его TTL.
        """
        payload = await self._client.get(f"{SCENARIO_KEY_PREFIX}{scenario_id}")
        return DynamicScenario.model_validate_json(payload) if payload is not None else None

    async def delete(self, scenario_id: str) -> None:
        """Удаляет ключ указанного сценария, включая повторную очистку.

        Args:
            scenario_id: Идентификатор удаляемого сценария.
        """
        await self._client.delete(f"{SCENARIO_KEY_PREFIX}{scenario_id}")
