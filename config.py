import os

from pydantic_settings import BaseSettings, SettingsConfigDict

from libs.config.grpc import GRPCServerConfig, GRPCClientConfig
from libs.config.http import HTTPServerConfig, HTTPClientConfig
from libs.config.kafka import KafkaClientConfig
from libs.config.postgres import PostgresConfig


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        extra='allow',
        env_file=os.environ.get('ENV_FILE'),
        env_file_encoding='utf-8',
        env_nested_delimiter='.'
    )

    users_http_client: HTTPClientConfig
    users_grpc_client: GRPCClientConfig

    cards_http_client: HTTPClientConfig
    cards_grpc_client: GRPCClientConfig

    gateway_http_server: HTTPServerConfig
    gateway_grpc_server: GRPCServerConfig

    accounts_http_client: HTTPClientConfig
    accounts_grpc_client: GRPCClientConfig

    operations_http_server: HTTPServerConfig
    operations_grpc_server: GRPCServerConfig
    operations_kafka_client: KafkaClientConfig
    operations_postgres_database: PostgresConfig


settings = Settings()
