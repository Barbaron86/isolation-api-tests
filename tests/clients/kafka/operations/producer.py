import logging
from collections.abc import Callable
from uuid import UUID

import allure

from tests.clients.kafka.producer import KafkaProducerTestClient
from tests.config import test_settings
from tests.schema.operations import OperationEventTestSchema
from tests.tools.config.kafka import KafkaClientTestConfig
from tests.tools.logger import get_test_logger
from tests.types.operations import OperationTestType, OperationTestStatus


class OperationsKafkaProducerTestClient(KafkaProducerTestClient):
    """Публикует события Operations с подтверждением доставки брокеру."""

    def __init__(
            self,
            config: KafkaClientTestConfig,
            logger: logging.Logger,
            *,
            delivery_timeout: float = 10.0,
            on_event: Callable[[OperationEventTestSchema], None] | None = None,
    ):
        """Создаёт producer и callback регистрации владения до отправки.

        Args:
            config: Конфигурация тестового брокера.
            logger: Логгер тестового слоя.
            delivery_timeout: Предельный срок подтверждения доставки.
            on_event: Регистрация события для очистки до публикации в Kafka.
        """
        super().__init__(config, logger, delivery_timeout=delivery_timeout)
        self.on_event = on_event

    def produce_operation_event_api(
            self,
            event: OperationEventTestSchema,
    ) -> OperationEventTestSchema:
        """Регистрирует событие и подтверждает только доставку брокеру.

        Обработка сервисом проверяется отдельным ожиданием через Operations API.
        Перед публикацией вызывается on_event, если он задан. Фикстура Operations
        связывает его с чтением исходных PostgreSQL ID и регистрацией cleanup;
        ошибка этого callback прерывает вызов до отправки сообщения.

        Args:
            event: Подготовленное событие и независимое ожидание теста.

        Returns:
            Исходный объект события без изменения полей.
        """
        with allure.step("Produce operation event and confirm Kafka delivery"):
            if self.on_event is not None:
                self.on_event(event)
            self.produce_and_wait(
                topic="operations-service.operation-event.inbox",
                value=event.model_dump_json(),
            )
        return event

    @allure.step("Produce in progress purchase operation event")
    def produce_in_progress_purchase_operation_event(
            self,
            *,
            user_id: UUID | None = None,
            card_id: UUID | None = None,
            account_id: UUID | None = None,
    ) -> OperationEventTestSchema:
        """Публикует покупку IN_PROGRESS с заданными либо новыми ID.

        Args:
            user_id: Пользователь; при отсутствии генерируется схемой.
            card_id: Карта; при отсутствии генерируется схемой.
            account_id: Счёт; при отсутствии генерируется схемой.

        Returns:
            Событие покупки с подтверждённой доставкой брокеру.
        """
        identifiers = {
            name: value for name, value in
            (("user_id", user_id), ("card_id", card_id), ("account_id", account_id))
            if value is not None
        }
        return self.produce_operation_event_api(
            OperationEventTestSchema(
                type=OperationTestType.PURCHASE,
                status=OperationTestStatus.IN_PROGRESS,
                **identifiers,
            )
        )

    @allure.step("Produce completed purchase operation event")
    def produce_completed_purchase_operation_event(
            self,
            *,
            user_id: UUID | None = None,
            card_id: UUID | None = None,
            account_id: UUID | None = None,
    ) -> OperationEventTestSchema:
        """Публикует завершённую покупку с заданными либо новыми ID.

        Args:
            user_id: Пользователь; при отсутствии генерируется схемой.
            card_id: Карта; при отсутствии генерируется схемой.
            account_id: Счёт; при отсутствии генерируется схемой.

        Returns:
            Событие покупки с подтверждённой доставкой брокеру.
        """
        identifiers = {
            name: value for name, value in
            (("user_id", user_id), ("card_id", card_id), ("account_id", account_id))
            if value is not None
        }
        return self.produce_operation_event_api(
            OperationEventTestSchema(
                type=OperationTestType.PURCHASE,
                status=OperationTestStatus.COMPLETED,
                **identifiers,
            )
        )


def build_operations_kafka_producer_test_client(
        *,
        on_event: Callable[[OperationEventTestSchema], None] | None = None,
) -> OperationsKafkaProducerTestClient:
    """Создаёт Operations producer из настроек тестового слоя.

    Args:
        on_event: Регистрация владения событием до публикации в Kafka.

    Returns:
        Клиент с настроенным сроком доставки и callback владения.
    """
    return OperationsKafkaProducerTestClient(
        config=test_settings.operations_kafka_client,
        logger=get_test_logger("OPERATIONS_KAFKA_PRODUCER_TEST_CLIENT"),
        delivery_timeout=test_settings.kafka_delivery_timeout,
        on_event=on_event,
    )
