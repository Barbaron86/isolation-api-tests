from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from tests.mock.scenarios import DynamicScenario


SCENARIO_KEY_PREFIX = "http-mock:scenarios:"
SCENARIO_TTL_SECONDS = 3600


class RedisScenarioStore:
    """Хранит динамические сценарии в общей для HTTP и gRPC базе Redis."""

    def __init__(self, client: Redis) -> None:
        """Принимает клиент, открытый на время жизни приложения.

        Args:
            client: Асинхронный Redis-клиент процесса мока.
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


@asynccontextmanager
async def open_redis_scenario_store(url: str) -> AsyncIterator[RedisScenarioStore]:
    """Открывает хранилище после проверки Redis и закрывает клиент при выходе.

    Args:
        url: Адрес общей базы сценариев.

    Yields:
        Хранилище с ограниченными таймаутами подключения и чтения.
    """
    async with Redis.from_url(
        url,
        socket_connect_timeout=2,
        socket_timeout=2,
        retry=Retry(NoBackoff(), 0),
    ) as client:
        await client.ping()
        yield RedisScenarioStore(client)
