from collections.abc import Iterator
from uuid import UUID

import pytest

from tests.clients.grpc.gateway.client import (
    GatewayGRPCTestClient,
    build_gateway_grpc_test_client,
)
from tests.clients.http.gateway.client import (
    GatewayHTTPTestClient,
    build_gateway_http_test_client,
)


@pytest.fixture
def active_credit_account_user_id() -> UUID:
    """Задаёт ID пользователя сценария активного кредитного счёта.

    Returns:
        Независимый от ответа Gateway UUID для запроса и ожидаемых связей.
    """
    return UUID("8b0e7c2a-1b6a-4e5d-9f1a-1b3f2a7c9e21")


@pytest.fixture
def active_debit_account_id() -> UUID:
    """Задаёт ID дебетового счёта из статических HTTP/gRPC-сценариев.

    Returns:
        UUID для запроса счёта и проверки связи его карт.
    """
    return UUID("99999999-aaaa-4bbb-8ccc-000000000001")


@pytest.fixture
def user_without_accounts_id() -> UUID:
    """Задаёт ID существующего пользователя без счетов в HTTP/gRPC-сценариях.

    Returns:
        UUID из подготовки сценария, отличный от пользователя с кредитным счётом.
    """
    return UUID("6e0a581c-57d4-4b81-9c67-14a4134ea02a")


@pytest.fixture
def account_without_cards_id() -> UUID:
    """Задаёт ID существующего счёта без карт в HTTP/gRPC-сценариях.

    Returns:
        UUID из подготовки сценария, отличный от счёта с картами.
    """
    return UUID("a7c43c93-7f5e-4bea-935d-9206715e8742")


@pytest.fixture
def user_with_multiple_accounts_id() -> UUID:
    """Задаёт ID пользователя с несколькими счетами в HTTP/gRPC-сценариях.

    Returns:
        Независимый от ответа UUID владельца двух подходящих счетов.
    """
    return UUID("f936dd1a-294f-46b5-9b13-b2a84453fed0")


@pytest.fixture
def account_with_mixed_cards_id() -> UUID:
    """Задаёт ID счёта с картами среди записей разных счетов в HTTP/gRPC-моках.

    Returns:
        UUID подготовленного дебетового счёта пользователя с несколькими счетами.
    """
    return UUID("7f86a8d5-2d3e-4e16-99ef-b06c53f4ea41")


@pytest.fixture
def unknown_user_id() -> UUID:
    """Задаёт ID пользователя, отсутствующий в HTTP/gRPC-мок-сценариях.

    Returns:
        Корректный UUID для проверки отсутствия пользователя, а не ошибки формата.
    """
    return UUID("00000000-0000-4000-8000-000000000099")


@pytest.fixture
def unknown_account_id() -> UUID:
    """Задаёт ID счёта, отсутствующий в HTTP/gRPC-мок-сценариях.

    Returns:
        Корректный UUID для проверки отсутствия счёта, а не ошибки формата.
    """
    return UUID("00000000-0000-4000-8000-000000000098")


@pytest.fixture
def gateway_http_test_client() -> GatewayHTTPTestClient:
    # Фикстура сценарного тестового слоя для HTTP-клиента gateway-service.
    #
    # Эта фикстура:
    # - не знает, какой сценарий будет использовать тест;
    # - не управляет поведением внешних интеграций;
    # - не выполняет HTTP-вызовы сама.
    #
    # Её единственная ответственность — предоставить тесту
    # корректно сконфигурированный HTTP API-клиент gateway-service,
    # через который тест будет взаимодействовать с системой.
    #
    # Все архитектурные решения уже зафиксированы на уровне клиента:
    # - конфигурация окружения берётся из test_settings;
    # - транспорт настроен централизованно;
    # - поддержка RequestContext и сценариев встроена в клиент.
    #
    # Фикстура лишь вызывает фабрику и возвращает готовый инструмент,
    # не вмешиваясь в бизнес-смысл теста.
    return build_gateway_http_test_client()


@pytest.fixture
def gateway_grpc_test_client() -> Iterator[GatewayGRPCTestClient]:
    """Предоставляет Gateway-клиент одному тесту и закрывает его канал после теста.

    Закрытие выполняется и при ошибке проверки или зависимой фикстуры.

    Yields:
        Клиент с отдельным gRPC-каналом, созданный существующей фабрикой.
    """
    client = build_gateway_grpc_test_client()
    try:
        yield client
    finally:
        client.channel.close()
