"""Фикстуры клиентов и принадлежащих тесту данных Operations."""

from collections.abc import Generator

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
from tests.config import test_settings
from tests.tools.cleanup import CleanupManager
from tests.tools.operations_cleanup import KafkaOperationsCleanup


@pytest.fixture
def operations_http_test_client() -> Generator[OperationsHTTPTestClient, None, None]:
    """Создаёт синхронный HTTP-клиент Operations для текущего теста.

    Yields:
        Клиент с конфигурацией и обработчиками HTTP-запросов тестового слоя.
    """
    client = build_operations_http_test_client()
    try:
        yield client
    finally:
        client.client.close()


@pytest.fixture
def operations_grpc_test_client() -> Generator[OperationsGRPCTestClient, None, None]:
    """Создаёт синхронный gRPC-клиент Operations для текущего теста.

    Yields:
        Обёртка над настроенным каналом и сгенерированным stub Operations.
    """
    client = build_operations_grpc_test_client()
    try:
        yield client
    finally:
        client.channel.close()


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
def operations_kafka_producer_test_client(
    cleanup_manager: CleanupManager,
    operations_postgres_test_repository: OperationsPostgresTestRepository,
) -> Generator[OperationsKafkaProducerTestClient, None, None]:
    """Создаёт Kafka producer операций для текущего теста.

    Args:
        cleanup_manager: Реестр действий текущего теста; решение о сохранении
            данных принимает pytest-фикстура cleanup_manager.
        operations_postgres_test_repository: Чтение ID и удаление своих строк.

    Yields:
        Producer с регистрацией отложенной сверки до отправки каждого события.
        Сверка использует PostgreSQL, поэтому не зависит от успешного ответа API.
        Producer закрывается до выполнения действий cleanup_manager.
    """
    cleanup = KafkaOperationsCleanup(
        operations_postgres_test_repository,
        cleanup_manager,
        timeout=test_settings.operations_processing_timeout,
        poll_interval=test_settings.operations_poll_interval,
    )
    producer = build_operations_kafka_producer_test_client(on_event=cleanup.track)
    try:
        yield producer
    finally:
        producer.close()
