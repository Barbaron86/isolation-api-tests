from typing import Any

import allure

from tests.tools.logger import get_test_logger

logger = get_test_logger("BASE_ASSERTIONS")


@allure.step("Check that {name} equals {expected:.60}")
def assert_equal(actual: Any, expected: Any, name: str) -> None:
    """Проверяет равенство значений и записывает результат в лог и Allure.

    В заголовке ожидаемое значение ограничено 60 символами. Полные значения
    доступны в параметрах шага, а при несовпадении — также в сообщении об ошибке.

    Args:
        actual: Полученное значение.
        expected: Ожидаемое значение.
        name: Название проверяемого поля или набора данных.

    Raises:
        AssertionError: Если значения не равны.
    """
    logger.info(f'Check that "{name}" equals {expected!r}')

    assert actual == expected, (
        f'Incorrect value: "{name}". '
        f'Expected value: {expected}. '
        f'Actual value: {actual}'
    )


@allure.step("Check that {name} contains {expected:.60}")
def assert_string_contains(actual: str, expected: str, name: str) -> None:
    """Проверяет строковый тип значения и наличие ожидаемого фрагмента.

    Проверка типа защищает от списков и словарей из JSON: оператор in для них
    проверяет элементы или ключи и может дать ложное совпадение со строкой.
    В заголовке ожидаемый фрагмент ограничен 60 символами. Полные значения
    доступны в параметрах шага и сообщении об ошибке.

    Args:
        actual: Полученное значение, которое должно быть строкой.
        expected: Фрагмент, который должен присутствовать в строке.
        name: Название проверяемого поля для Allure и диагностики.

    Raises:
        AssertionError: Если значение не строка либо фрагмент отсутствует.
    """
    logger.info(f'Check that "{name}" contains {expected!r}')
    assert isinstance(actual, str), f'Incorrect type: "{name}". Expected str. Actual value: {actual!r}'
    assert expected in actual, (
        f'Incorrect value: "{name}". '
        f'Expected substring: {expected!r}. Actual value: {actual!r}'
    )
