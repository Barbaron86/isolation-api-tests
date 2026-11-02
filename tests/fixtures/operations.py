"""Фикстуры клиентов и прямой подготовки данных Operations."""

import pytest

from tests.clients.grpc.operations.client import (
    build_operations_grpc_test_client,
    OperationsGRPCTestClient,
)
from tests.clients.http.operations.client import (
    build_operations_http_test_client,
    OperationsHTTPTestClient,
)
from tests.clients.kafka.operations.producer import (
    OperationsKafkaProducerTestClient,
    build_operations_kafka_producer_test_client,
)
from tests.clients.postgres.operations.repository import (
    OperationsPostgresTestRepository,
    get_operations_postgres_test_repository,
)
from tests.tools.cleanup import CleanupManager


@pytest.fixture
def operations_http_test_client() -> OperationsHTTPTestClient:
    """Создаёт синхронный HTTP-клиент Operations для текущего теста.

    Returns:
        Клиент с конфигурацией и обработчиками HTTP-запросов тестового слоя.
    """
    return build_operations_http_test_client()


@pytest.fixture
def operations_grpc_test_client() -> OperationsGRPCTestClient:
    """Создаёт синхронный gRPC-клиент Operations для текущего теста.

    Returns:
        Обёртка над настроенным каналом и сгенерированным stub Operations.
    """
    return build_operations_grpc_test_client()


@pytest.fixture
def operations_postgres_test_repository(
    cleanup_manager: CleanupManager,
) -> OperationsPostgresTestRepository:
    """Предоставляет repository с учётом строк, вставленных текущим тестом.

    Args:
        cleanup_manager: Реестр действий очистки для одного теста.

    Returns:
        Repository с автоматической регистрацией удаления по ID. Зависимая
        фикстура cleanup_manager завершает очистку или пропускает её по политике
        сохранения, включая ошибки последующей подготовки или самого теста.
    """
    return get_operations_postgres_test_repository(cleanup_manager=cleanup_manager)


@pytest.fixture
def operations_kafka_producer_test_client() -> OperationsKafkaProducerTestClient:
    """Создаёт Kafka producer операций для текущего теста.

    Returns:
        Клиент публикации OperationEventTestSchema во входной топик Operations.
        Политика очистки прямой подготовки PostgreSQL к его событиям не применяется.
    """
    return build_operations_kafka_producer_test_client()
