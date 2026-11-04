"""Общие проверки HTTP-статуса ответа."""

from http import HTTPStatus

from tests.assertions.base import assert_equal


def assert_status_code(actual: int, expected: HTTPStatus) -> None:
    """Проверяет точный HTTP-статус до разбора тела ответа.

    Общая проверка равенства создаёт единственный шаг Allure с обоими значениями.

    Args:
        actual: Статус полученного HTTP-ответа.
        expected: Ожидаемый статус из HTTPStatus.

    Raises:
        AssertionError: Если полученный статус отличается от ожидаемого.
    """
    assert_equal(actual, expected, "HTTP status code")
