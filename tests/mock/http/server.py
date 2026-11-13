from argparse import ArgumentParser
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import partial
from http import HTTPStatus

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from tests.config import test_settings
from tests.mock.http.api.accounts import build_accounts_mock_router
from tests.mock.http.api.cards import build_cards_mock_router
from tests.mock.http.api.scenarios import admin_scenarios_router
from tests.mock.http.api.users import build_users_mock_router
from tests.mock.redis_store import open_redis_scenario_store
from tests.mock.scenarios import InMemoryScenarioStore


@asynccontextmanager
async def redis_lifespan(app: FastAPI, *, redis_url: str) -> AsyncIterator[None]:
    """Открывает один Redis-клиент на воркер и закрывает его при остановке.

    Args:
        app: Приложение воркера, которому нужно хранилище.
        redis_url: Адрес общего Redis.

    Yields:
        Управление приложению после успешной проверки соединения.
    """
    async with open_redis_scenario_store(redis_url) as store:
        app.state.scenario_store = store
        yield


async def scenario_store_unavailable(_request: Request, _error: Exception) -> JSONResponse:
    """Возвращает HTTP 503 при сетевой ошибке Redis.

    Args:
        _request: Запрос к хранилищу сценариев.
        _error: Ошибка соединения или таймаут Redis.

    Returns:
        Ответ о недоступности хранилища без деталей подключения.
    """
    return JSONResponse(
        status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        content={"detail": "Mock scenario storage unavailable"},
    )


def create_app(*, enable_dynamic_scenarios: bool = False, redis_url: str | None = None) -> FastAPI:
    """Собирает HTTP-мок со встроенными и опциональными динамическими сценариями.

    Args:
        enable_dynamic_scenarios: Подключает Admin API и динамические сценарии зависимостей Gateway.
        redis_url: Адрес Redis. При None сценарии хранятся в памяти приложения.

    Returns:
        FastAPI-приложение с маршрутами зависимостей Gateway.

    Raises:
        ValueError: Если задан Redis при выключенных динамических сценариях.
    """
    if redis_url is not None and not enable_dynamic_scenarios:
        raise ValueError("Redis requires dynamic mock scenarios")

    lifespan = partial(redis_lifespan, redis_url=redis_url) if redis_url is not None else None
    app = FastAPI(title="mock-service", lifespan=lifespan)
    if enable_dynamic_scenarios:
        if redis_url is None:
            app.state.scenario_store = InMemoryScenarioStore()
        else:
            app.add_exception_handler(RedisConnectionError, scenario_store_unavailable)
            app.add_exception_handler(RedisTimeoutError, scenario_store_unavailable)
        app.include_router(admin_scenarios_router)

    app.include_router(build_users_mock_router(enable_dynamic_scenarios=enable_dynamic_scenarios))
    app.include_router(build_cards_mock_router(enable_dynamic_scenarios=enable_dynamic_scenarios))
    app.include_router(build_accounts_mock_router(enable_dynamic_scenarios=enable_dynamic_scenarios))
    return app


def create_dynamic_app() -> FastAPI:
    """Создаёт приложение динамического HTTP-мока внутри воркера Uvicorn.

    Returns:
        Приложение с хранилищем, выбранным настройкой MOCK_REDIS_URL.
    """
    redis_url = test_settings.mock_redis_url
    return create_app(enable_dynamic_scenarios=True, redis_url=str(redis_url) if redis_url else None)


app = create_app()

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--dynamic-scenarios", action="store_true")
    arguments = parser.parse_args()

    application = (
        "tests.mock.http.server:create_dynamic_app" if arguments.dynamic_scenarios else "tests.mock.http.server:app"
    )
    use_process_memory = arguments.dynamic_scenarios and test_settings.mock_redis_url is None
    uvicorn.run(
        app=application,
        factory=arguments.dynamic_scenarios,
        host=str(test_settings.mock_http_server.address),
        port=test_settings.mock_http_server.port,
        workers=1 if use_process_memory else 3,
    )
