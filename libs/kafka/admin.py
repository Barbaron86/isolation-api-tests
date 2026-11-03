"""Создание Kafka-топиков с явным распространением ошибок брокера."""

from logging import Logger

from confluent_kafka import KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic

from libs.config.kafka import KafkaClientConfig


class KafkaAdminClient:
    """Управляет топиками приложения через Kafka Admin API."""

    def __init__(self, config: KafkaClientConfig, logger: Logger) -> None:
        """Создаёт admin-клиент с настройками брокера и логгером.

        Args:
            config: Адрес брокера приложения.
            logger: Логирование результата создания топиков.
        """
        self.admin = AdminClient({'bootstrap.servers': config.bootstrap_servers})
        self.logger = logger

    def create_topic(self, topic: str, num_partitions: int = 1, replication_factor: int = 1):
        """Создаёт топик; допускает только ошибку его существования.

        Args:
            topic: Имя топика.
            num_partitions: Число партиций.
            replication_factor: Число реплик.

        Raises:
            KafkaException: Если брокер отклонил создание по другой причине.
        """
        new_topic = NewTopic(
            topic,
            num_partitions=num_partitions,
            replication_factor=replication_factor
        )
        futures = self.admin.create_topics([new_topic], request_timeout=30)

        for topic_name, future in futures.items():
            try:
                future.result(timeout=35)
                self.logger.info(f"Kafka topic '{topic_name}' created")
            except KafkaException as error:
                if error.args[0].code() == KafkaError.TOPIC_ALREADY_EXISTS:
                    self.logger.info(f"Topic '{topic_name}' already exists")
                else:
                    self.logger.error("Kafka topic creation failed topic=%s code=%s", topic_name, error.args[0].code())
                    raise
