import logging
import math
from collections.abc import Callable
from time import monotonic

import allure
from confluent_kafka import KafkaError, KafkaException, Message, Producer

from tests.tools.config.kafka import KafkaClientTestConfig


class KafkaProducerTestClient:
    """Ставит сообщения в очередь и явно проверяет доставку брокеру."""

    def __init__(
            self,
            config: KafkaClientTestConfig,
            logger: logging.Logger,
            *,
            delivery_timeout: float = 10.0,
    ):
        """Создаёт producer с ограниченным временем ожидания доставки.

        Args:
            config: Адрес тестового брокера.
            logger: Логгер тестового слоя.
            delivery_timeout: Максимальный срок flush в секундах.
        """
        self.logger = logger
        self.delivery_timeout = self._validate_timeout(delivery_timeout)
        self._closed = False
        self.producer = Producer({"bootstrap.servers": config.bootstrap_servers})

    @staticmethod
    def _validate_timeout(timeout: float) -> float:
        """Отклоняет сроки, допускающие неограниченное ожидание.

        Args:
            timeout: Предельное время ожидания в секундах.

        Returns:
            Проверенный срок ожидания.

        Raises:
            ValueError: Срок отрицательный или не является конечным числом.
        """
        if not math.isfinite(timeout) or timeout < 0:
            raise ValueError("Kafka timeout must be finite and non-negative")
        return timeout

    def produce(
            self,
            topic: str,
            value: str | bytes,
            *,
            on_delivery: Callable[[KafkaError | None, Message], None] | None = None,
    ) -> None:
        """Ставит сообщение в очередь без обещания его доставки.

        Args:
            topic: Топик назначения.
            value: Сериализованное сообщение.
            on_delivery: Callback результата конкретного сообщения.

        Raises:
            RuntimeError: Клиент уже закрыт.
            BufferError: Локальная очередь producer переполнена.
            KafkaException: Kafka отклонила постановку сообщения в очередь.
        """
        if self._closed:
            raise RuntimeError("Kafka producer is closed")
        with allure.step(f"Enqueue Kafka message: topic={topic}"):
            self.producer.produce(topic=topic, value=value, on_delivery=on_delivery)
            self.logger.info("Kafka message enqueued: topic=%s", topic)

    def produce_and_wait(
            self,
            topic: str,
            value: str | bytes,
            *,
            timeout: float | None = None,
    ) -> Message:
        """Один раз отправляет сообщение и проверяет результат доставки.

        Контекст ошибки содержит topic, остаток очереди и время ожидания;
        содержимое события в диагностику не включается. Неопределённая доставка
        по timeout не отменяет сообщение, оставшееся в очереди producer.

        Args:
            topic: Топик назначения.
            value: Сериализованное сообщение.
            timeout: Срок доставки; по умолчанию используется настройка клиента.

        Returns:
            Подтверждённое сообщение с partition и offset брокера.

        Raises:
            KafkaException: Callback сообщил об ошибке доставки.
            TimeoutError: Осталась очередь либо callback не подтвердил доставку.
        """
        timeout = self._validate_timeout(self.delivery_timeout if timeout is None else timeout)
        delivery_result: list[tuple[KafkaError | None, Message]] = []

        def on_delivery(error: KafkaError | None, message: Message) -> None:
            """Сохраняет результат доставки только отправляемого сообщения.

            Args:
                error: Ошибка доставки либо None при успехе.
                message: Сообщение из delivery report брокера.
            """
            delivery_result.append((error, message))

        started_at = monotonic()
        with allure.step(f"Confirm Kafka delivery: topic={topic}, timeout={timeout}s"):
            self.produce(topic, value, on_delivery=on_delivery)
            pending = self.producer.flush(timeout=timeout)
            elapsed = monotonic() - started_at
            delivery_context = (
                f"topic={topic}, timeout={timeout}s, pending={pending}, "
                f"callback={bool(delivery_result)}, elapsed={elapsed:.3f}s"
            )
            if delivery_result and delivery_result[0][0] is not None:
                error = KafkaException(delivery_result[0][0])
                error.add_note(f"Kafka delivery failed: {delivery_context}")
                raise error
            if pending or not delivery_result:
                raise TimeoutError(f"Kafka delivery unconfirmed: {delivery_context}")
            message = delivery_result[0][1]
            self.logger.info(
                "Kafka delivery confirmed: topic=%s partition=%s offset=%s elapsed=%.3fs",
                topic, message.partition(), message.offset(), elapsed,
            )
            return message

    def flush_all(self, timeout: float | None = None) -> None:
        """Ожидает опустошения очереди, не заменяя проверку delivery callback.

        Args:
            timeout: Срок ожидания; по умолчанию используется настройка клиента.

        Raises:
            TimeoutError: По завершении срока в очереди остались сообщения.
        """
        timeout = self._validate_timeout(self.delivery_timeout if timeout is None else timeout)
        pending = self.producer.flush(timeout=timeout)
        if pending:
            raise TimeoutError(f"Kafka flush timed out: timeout={timeout}s, pending={pending}")

    def close(self, timeout: float | None = None) -> None:
        """Запрещает новые отправки и явно завершает ограниченный flush.

        Args:
            timeout: Максимальный срок завершающего flush в секундах.

        Raises:
            TimeoutError: Остались сообщения с неопределённой доставкой.
        """
        if self._closed:
            return
        self._closed = True
        self.flush_all(timeout=timeout)
