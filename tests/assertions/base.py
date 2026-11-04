from typing import Any

import allure

from tests.tools.logger import get_test_logger

logger = get_test_logger("BASE_ASSERTIONS")


@allure.step("Check that {name} equals expected value")
def assert_equal(actual: Any, expected: Any, name: str) -> None:
    """Проверяет равенство значений и записывает результат в лог и Allure.

    Заголовок шага содержит только название поля. Значения доступны в параметрах
    шага, а при несовпадении — также в сообщении об ошибке.

    Args:
        actual: Полученное значение.
        expected: Ожидаемое значение.
        name: Название проверяемого поля или набора данных.

    Raises:
        AssertionError: Если значения не равны.
    """
    logger.info(f'Check that "{name}" equals {expected}')

    assert actual == expected, (
        f'Incorrect value: "{name}". '
        f'Expected value: {expected}. '
        f'Actual value: {actual}'
    )


@allure.step('Check that "{name}" contains "{expected}"')
def assert_string_contains(actual: str, expected: str, name: str) -> None:
    """Проверяет строковый тип значения и наличие ожидаемого фрагмента.

    Проверка типа защищает от списков и словарей из JSON: оператор in для них
    проверяет элементы или ключи и может дать ложное совпадение со строкой.

    Args:
        actual: Полученное значение, которое должно быть строкой.
        expected: Фрагмент, который должен присутствовать в строке.
        name: Название проверяемого поля для Allure и диагностики.

    Raises:
        AssertionError: Если значение не строка либо фрагмент отсутствует.
    """
    logger.info('Check that "%s" contains %r', name, expected)
    assert isinstance(actual, str), f'Incorrect type: "{name}". Expected str. Actual value: {actual!r}'
    assert expected in actual, (
        f'Incorrect value: "{name}". '
        f'Expected substring: {expected!r}. Actual value: {actual!r}'
    )
