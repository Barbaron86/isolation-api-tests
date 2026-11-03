"""Чтение Kafka с сигналом готовности после назначения начальных позиций."""

import asyncio
from logging import Logger
from pathlib import Path
from typing import Awaitable, Callable

from aiokafka import AIOKafkaConsumer, ConsumerRebalanceListener

from libs.config.kafka import KafkaClientConfig

KafkaConsumerHandler = Callable[[str], Awaitable[None]]


class KafkaReadinessListener(ConsumerRebalanceListener):
    """Поддерживает файл готовности только для назначенных партиций."""

    def __init__(self, consumer: AIOKafkaConsumer, path: Path, logger: Logger) -> None:
        """Связывает назначение партиций с локальным сигналом готовности.

        Args:
            consumer: Consumer, начальные позиции которого нужно подтвердить.
            path: Файл, проверяемый healthcheck текущего контейнера.
            logger: Логирование безопасных технических сведений.
        """
        self.consumer = consumer
        self.path = path
        self.logger = logger
        self.error: Exception | None = None

    async def on_partitions_revoked(self, revoked):
        """Удаляет сигнал перед отзывом партиций и новым назначением.

        Args:
            revoked: Отзываемые партиции из callback Kafka.
        """
        self.path.unlink(missing_ok=True)

    async def on_partitions_assigned(self, assigned):
        """Ждёт начальные позиции до публикации сигнала готовности.

        Args:
            assigned: Назначенные consumer партиции.
        """
        self.path.unlink(missing_ok=True)
        if not assigned:
            return
        try:
            async with asyncio.timeout(45):
                for partition in assigned:
                    await self.consumer.position(partition)
            self.path.write_text("ready\n", encoding="utf-8")
            self.logger.info("Kafka consumer ready partitions=%s", len(assigned))
        except Exception as error:
            self.error = error
            raise


class KafkaConsumerClient:
    """Передаёт сообщения обработчику и закрывает consumer при завершении."""

    def __init__(self, config: KafkaClientConfig, logger: Logger) -> None:
        """Сохраняет зависимости; readiness_file при необходимости задаёт сервис.

        Args:
            config: Адрес брокера приложения.
            logger: Логирование состояния consumer без содержимого сообщений.
        """
        self.config = config
        self.logger = logger
        self.readiness_file: Path | None = None

    async def start(self, topic: str, group_id: str, handler: KafkaConsumerHandler):
        """Читает топик после назначения партиций и начальных позиций.

        Args:
            topic: Топик приложения.
            group_id: Группа consumer.
            handler: Асинхронный обработчик содержимого сообщения.
        """
        if self.readiness_file is not None:
            self.readiness_file.unlink(missing_ok=True)
        consumer = AIOKafkaConsumer(
            group_id=group_id,
            bootstrap_servers=self.config.bootstrap_servers,
        )
        listener = (
            KafkaReadinessListener(consumer, self.readiness_file, self.logger)
            if self.readiness_file is not None else None
        )
        consumer.subscribe(topics=[topic], listener=listener)
        failed = False
        try:
            async with asyncio.timeout(60):
                await consumer.start()
            if listener is not None and listener.error is not None:
                raise listener.error
            self.logger.info("Kafka consumer started topic=%s", topic)
            async for message in consumer:
                if listener is not None and listener.error is not None:
                    raise listener.error
                self.logger.info(
                    "Received Kafka record topic=%s partition=%s offset=%s",
                    message.topic, message.partition, message.offset,
                )
                await handler(message.value.decode("utf-8"))
                self.logger.info(
                    "Processed Kafka record topic=%s partition=%s offset=%s",
                    message.topic, message.partition, message.offset,
                )
        except BaseException:
            failed = True
            raise
        finally:
            if self.readiness_file is not None:
                self.readiness_file.unlink(missing_ok=True)
            try:
                async with asyncio.timeout(10):
                    await consumer.stop()
                self.logger.info("Kafka consumer stopped")
            except Exception as error:
                if not failed:
                    raise
                self.logger.error("Kafka consumer stop failed error_type=%s", type(error).__name__)
