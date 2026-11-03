"""Ограниченное ожидание точного количества операций через HTTP или gRPC."""

from collections.abc import Callable
from math import isfinite
from time import monotonic, sleep

from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsResponse
from tests.config import test_settings
from tests.schema.operations import GetOperationsResponseTestSchema


def wait_for_operations_count[
    ResponseT: (GetOperationsResponseTestSchema, GetOperationsResponse)
](
        read_operations: Callable[[float], ResponseT],
        *,
        expected_count: int,
        description: str,
        timeout: float | None = None,
        interval: float | None = None,
) -> ResponseT:
    """Ожидает точное количество операций, повторяя только неполный результат.

    Чтение получает оставшийся бюджет и отвечает за транспортные ограничения,
    статус и схему. Его исключения распространяются без повторных попыток.
    Поздний ответ не принимается даже при точном количестве; прервать само
    синхронное чтение helper не может. Поля операций проверяет вызывающий тест.

    Args:
        read_operations: Однократное чтение с timeout в секундах; возвращает
            модель успешного HTTP-ответа или protobuf-ответ со списком operations.
        expected_count: Точное неотрицательное целое количество; bool запрещён.
        description: Фильтры или другой контекст запроса для диагностики.
        timeout: Общий срок в секундах; None использует operations_processing_timeout.
        interval: Пауза в секундах; None использует operations_poll_interval.
            Последняя пауза ограничивается оставшимся временем.

    Returns:
        Тот же объект ответа, в котором до срока наблюдалось точное количество.

    Raises:
        ValueError: При недопустимом количестве, неконечном или неположительном
            timeout либо interval.
        TimeoutError: Если срок истёк до получения точного количества.
        AssertionError: Если ответ содержит больше операций, чем ожидалось.
    """
    timeout = test_settings.operations_processing_timeout if timeout is None else timeout
    interval = test_settings.operations_poll_interval if interval is None else interval
    if isinstance(expected_count, bool) or not isinstance(expected_count, int) or expected_count < 0:
        raise ValueError("expected_count must be a non-negative integer")
    if not isfinite(timeout) or timeout <= 0 or not isfinite(interval) or interval <= 0:
        raise ValueError("timeout and interval must be finite positive numbers")

    deadline = monotonic() + timeout
    attempts = 0
    last_count = None
    while (remaining := deadline - monotonic()) > 0:
        attempts += 1
        get_operations_response_data = read_operations(remaining)
        last_count = len(get_operations_response_data.operations)
        assert last_count <= expected_count, (
            f"Extra operations: expected_count={expected_count}, actual_count={last_count}; "
            f"{description}, attempts={attempts}"
        )
        remaining = deadline - monotonic()
        if remaining <= 0:
            break
        if last_count == expected_count:
            return get_operations_response_data
        sleep(min(interval, remaining))

    raise TimeoutError(
        f"Expected operation count was not observed within {timeout:g}s: {description}, "
        f"expected_count={expected_count}, last_count={last_count}, attempts={attempts}"
    )
