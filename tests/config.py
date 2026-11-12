"""Настройки клиентов и ограниченного ожидания асинхронных Operations-сценариев."""

from pydantic import Field, HttpUrl, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from tests.tools.config.grpc import GRPCClientTestConfig
from tests.tools.config.grpc import GRPCServerTestConfig
from tests.tools.config.http import HTTPClientTestConfig
from tests.tools.config.http import HTTPServerTestConfig
from tests.tools.config.kafka import KafkaClientTestConfig
from tests.tools.config.postgres import PostgresClientTestConfig


class TestSettings(BaseSettings):
    """Загружает настройки тестового слоя из окружения и tests/.env.

    Attributes:
        mock_admin_http_client: Адрес и таймаут для регистрации HTTP-сценариев.
        mock_redis_url: Адрес общего хранилища динамических HTTP-сценариев.
        kafka_delivery_timeout: Срок подтверждения доставки одного события, секунды.
        operations_processing_timeout: Срок появления операций через API, секунды.
        operations_poll_interval: Пауза между чтениями неполной выборки, секунды.
    """

    model_config = SettingsConfigDict(
        extra="allow",
        env_file="./tests/.env",
        env_file_encoding="utf-8",
        env_nested_delimiter=".",
    )

    operations_postgres_client: PostgresClientTestConfig

    mock_http_server: HTTPServerTestConfig
    mock_grpc_server: GRPCServerTestConfig
    mock_admin_http_client: HTTPClientTestConfig = Field(
        default_factory=lambda: HTTPClientTestConfig(url=HttpUrl("http://127.0.0.1:8003"), timeout=10.0)
    )
    mock_redis_url: RedisDsn | None = None

    gateway_http_client: HTTPClientTestConfig
    gateway_grpc_client: GRPCClientTestConfig

    operations_http_client: HTTPClientTestConfig
    operations_grpc_client: GRPCClientTestConfig
    operations_kafka_client: KafkaClientTestConfig

    kafka_delivery_timeout: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    operations_processing_timeout: float = Field(default=10.0, gt=0, allow_inf_nan=False)
    operations_poll_interval: float = Field(default=0.25, gt=0, allow_inf_nan=False)


test_settings = TestSettings()
