"""Запуск Kafka-обработки Operations с локальным сигналом готовности."""

import asyncio
from pathlib import Path

from services.operations.app.controllers.kafka import handle_operation_events
from services.operations.services.kafka.consumer import (
    get_operations_kafka_admin_client,
    get_operations_kafka_consumer_client,
)
from services.operations.services.kafka.topics import OperationsKafkaTopic
from services.operations.services.postgres.repositories.operations import get_operations_repository


async def consume():
    """Создаёт топики и запускает consumer после удаления старого readiness."""
    readiness_file = Path("/tmp/operations-kafka.ready")
    readiness_file.unlink(missing_ok=True)
    operations_repository = get_operations_repository()
    operations_kafka_admin_client = get_operations_kafka_admin_client()
    operations_kafka_consumer_client = get_operations_kafka_consumer_client()
    operations_kafka_consumer_client.readiness_file = readiness_file

    for topic in OperationsKafkaTopic:
        operations_kafka_admin_client.create_topic(
            topic=topic,
            num_partitions=1,
            replication_factor=1
        )

    await asyncio.gather(
        operations_kafka_consumer_client.consume_operation_events(
            handler=handle_operation_events(operations_repository)
        ),
    )


if __name__ == '__main__':
    asyncio.run(consume())
