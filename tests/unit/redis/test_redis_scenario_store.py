import asyncio
import json
from unittest.mock import AsyncMock, Mock, call
from uuid import uuid4

import pytest
from redis.asyncio import Redis
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from tests.mock.http.redis_store import RedisScenarioStore
from tests.mock.http.scenarios import DynamicScenario
from tests.schema.mock_gateway import GatewayMockOperation, GatewayMockScenarioTestSchema
from tests.tools.gateway_data import make_account, make_card, make_user


@pytest.mark.parametrize("scenario_shape", ["single-card", "account-with-cards", "gateway"])
def test_scenario_round_trip_preserves_payload_and_sets_ttl(scenario_shape: str) -> None:
    """Проверяет сохранение JSON с TTL и чтение модели для каждой формы сценария.

    Args:
        scenario_shape: Форма данных, которую принимает Admin API.
    """
    user = make_user()
    account = make_account(user_id=user.id)
    card = make_card(account_id=account.id)
    payloads = {
        "single-card": {"card": card},
        "account-with-cards": {"account": account, "cards": [card]},
        "gateway": {
            "gateway": GatewayMockScenarioTestSchema(
                users=[user], accounts=[account], cards=[card], unavailable=[GatewayMockOperation.GET_CARDS],
            ),
        },
    }
    scenario = DynamicScenario(id=f"dynamic-{uuid4()}", **payloads[scenario_shape])
    key = f"http-mock:scenarios:{scenario.id}"
    expected_payload = scenario.model_dump(mode="json", exclude_none=True)
    redis_client = Mock(
        spec_set=Redis,
        set=AsyncMock(return_value=True),
        get=AsyncMock(return_value=json.dumps(expected_payload).encode("utf-8")),
    )
    store = RedisScenarioStore(redis_client)

    asyncio.run(store.save(scenario))
    restored_scenario = asyncio.run(store.get(scenario.id))

    redis_client.set.assert_awaited_once()
    saved_key, saved_json = redis_client.set.await_args.args
    assert saved_key == key
    assert json.loads(saved_json) == expected_payload
    assert redis_client.set.await_args.kwargs["ex"] == 3600
    redis_client.get.assert_awaited_once_with(key)
    assert restored_scenario == scenario


def test_repeated_deletion_and_missing_read_use_the_exact_scenario_key() -> None:
    """Проверяет команды удаления и чтения отсутствующего ключа сценария."""
    scenario_id = f"dynamic-{uuid4()}"
    key = f"http-mock:scenarios:{scenario_id}"
    redis_client = Mock(
        spec_set=Redis,
        get=AsyncMock(return_value=None),
        delete=AsyncMock(side_effect=[1, 0]),
    )
    store = RedisScenarioStore(redis_client)

    asyncio.run(store.delete(scenario_id))
    asyncio.run(store.delete(scenario_id))
    restored_scenario = asyncio.run(store.get(scenario_id))

    assert restored_scenario is None
    redis_client.get.assert_awaited_once_with(key)
    assert redis_client.delete.await_args_list == [call(key), call(key)]


def test_get_propagates_redis_connection_error() -> None:
    """Передаёт исходную ошибку Redis вызывающему коду."""
    connection_error = RedisConnectionError("Redis is unavailable")
    redis_client = Mock(spec_set=Redis, get=AsyncMock(side_effect=connection_error))
    store = RedisScenarioStore(redis_client)

    with pytest.raises(RedisConnectionError) as error:
        asyncio.run(store.get(f"dynamic-{uuid4()}"))

    assert error.value is connection_error


def test_save_propagates_redis_connection_error() -> None:
    """Ошибка записи остаётся видимой вызывающему коду регистрации."""
    scenario = DynamicScenario(id=f"dynamic-{uuid4()}", gateway=GatewayMockScenarioTestSchema())
    connection_error = RedisConnectionError("Redis is unavailable")
    redis_client = Mock(spec_set=Redis, set=AsyncMock(side_effect=connection_error))
    store = RedisScenarioStore(redis_client)

    with pytest.raises(RedisConnectionError) as error:
        asyncio.run(store.save(scenario))

    assert error.value is connection_error
    redis_client.set.assert_awaited_once()


def test_delete_propagates_redis_timeout() -> None:
    """Таймаут удаления остаётся видимым вызывающему коду очистки."""
    scenario_id = f"dynamic-{uuid4()}"
    timeout_error = RedisTimeoutError("Redis timed out")
    redis_client = Mock(spec_set=Redis, delete=AsyncMock(side_effect=timeout_error))
    store = RedisScenarioStore(redis_client)

    with pytest.raises(RedisTimeoutError) as error:
        asyncio.run(store.delete(scenario_id))

    assert error.value is timeout_error
    redis_client.delete.assert_awaited_once_with(f"http-mock:scenarios:{scenario_id}")
