import asyncio
from concurrent import futures
from contextlib import AsyncExitStack

import grpc
from grpc_reflection.v1alpha import reflection

from contracts.services.accounts import accounts_service_pb2_grpc, accounts_service_pb2
from contracts.services.cards import cards_service_pb2, cards_service_pb2_grpc
from contracts.services.users import users_service_pb2, users_service_pb2_grpc
from tests.config import test_settings
from tests.mock.grpc.api.accounts import AccountsMockService
from tests.mock.grpc.api.cards import CardsMockService
from tests.mock.grpc.api.users import UsersMockService
from tests.mock.redis_store import open_redis_scenario_store
from tests.mock.scenarios import ScenarioStore


async def serve() -> None:
    """Запускает мок с Redis на время работы сервера, если задан его адрес."""
    async with AsyncExitStack() as resources:
        scenario_store = None
        if test_settings.mock_redis_url is not None:
            scenario_store = await resources.enter_async_context(
                open_redis_scenario_store(str(test_settings.mock_redis_url))
            )
        await serve_rpc(scenario_store)


async def serve_rpc(scenario_store: ScenarioStore | None) -> None:
    """Регистрирует сервисы и останавливает gRPC до закрытия Redis.

    Args:
        scenario_store: Общее хранилище динамических ответов gRPC-мока.
    """
    # gRPC мок-сервис запускается как отдельный инфраструктурный процесс.
    # Он моделирует внешний мир для gateway и любых других клиентов,
    # оставаясь "честным" gRPC сервером: сетевые вызовы, реальные контракты,
    # никакого знания о тестах и о том, кто именно является клиентом.

    server = grpc.aio.server(futures.ThreadPoolExecutor(max_workers=10))

    # Адрес берём из конфигурации тестового окружения,
    # чтобы одинаково работать локально и в Docker,
    # и не хардкодить сетевые параметры в коде.
    server.add_insecure_port(test_settings.mock_grpc_server.url)

    # Регистрируем сервисы строго по protobuf-контрактам.
    # Здесь нет сценарной логики: сервер лишь собирает компоненты вместе.
    users_service_pb2_grpc.add_UsersServiceServicer_to_server(UsersMockService(scenario_store), server)
    cards_service_pb2_grpc.add_CardsServiceServicer_to_server(CardsMockService(scenario_store), server)
    accounts_service_pb2_grpc.add_AccountsServiceServicer_to_server(AccountsMockService(scenario_store), server)

    # Reflection нужен для инструментария (например, Postman/grpcurl)
    # и для удобной отладки на учебном стенде.
    #
    # Он не является частью "логики" мок-сервиса,
    # а лишь инфраструктурная возможность заглянуть в контракт сервера.
    reflection.enable_server_reflection(
        (
            reflection.SERVICE_NAME,
            users_service_pb2.DESCRIPTOR.services_by_name['UsersService'].full_name,
            cards_service_pb2.DESCRIPTOR.services_by_name['CardsService'].full_name,
            accounts_service_pb2.DESCRIPTOR.services_by_name['AccountsService'].full_name,

        ),
        server
    )

    try:
        await server.start()
        await server.wait_for_termination()
    finally:
        await server.stop(0)


if __name__ == '__main__':
    asyncio.run(serve())
