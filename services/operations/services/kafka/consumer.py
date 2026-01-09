from config import settings
from libs.kafka.admin import KafkaAdminClient
from libs.kafka.consumer import KafkaConsumerClient, KafkaConsumerHandler
from libs.logger import get_logger
from services.operations.services.kafka.topics import OperationsKafkaTopic


class OperationsKafkaConsumerClient(KafkaConsumerClient):
    async def consume_operation_events(self, handler: KafkaConsumerHandler):
        await self.start(
            topic=OperationsKafkaTopic.OPERATION_EVENTS_INBOX,
            group_id="operation-events-group",
            handler=handler
        )


def get_operations_kafka_admin_client() -> KafkaAdminClient:
    logger = get_logger("OPERATIONS_KAFKA_ADMIN_CLIENT")
    return KafkaAdminClient(config=settings.operations_kafka_client, logger=logger)


def get_operations_kafka_consumer_client() -> OperationsKafkaConsumerClient:
    logger = get_logger("OPERATIONS_KAFKA_CONSUMER_CLIENT")
    return OperationsKafkaConsumerClient(config=settings.operations_kafka_client, logger=logger)
