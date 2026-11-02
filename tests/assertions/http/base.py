"""Общие проверки HTTP-статуса ответа."""

from http import HTTPStatus

import allure

from tests.assertions.base import assert_equal


@allure.step("Check HTTP status code: {expected}")
def assert_status_code(actual: int, expected: HTTPStatus) -> None:
    """Проверяет точный HTTP-статус до разбора тела ответа.

    Args:
        actual: Статус полученного HTTP-ответа.
        expected: Ожидаемый статус из HTTPStatus.
    """
    assert_equal(actual, expected, "HTTP status code")
