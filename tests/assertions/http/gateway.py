from http import HTTPStatus

import allure
from httpx import Response

from tests.assertions.base import assert_equal, assert_string_contains
from tests.assertions.http.base import assert_status_code
from tests.assertions.http.accounts import assert_account
from tests.assertions.http.cards import assert_card
from tests.assertions.http.users import assert_user
from tests.schema.gateway import (
    UserDetailsTestSchema,
    AccountDetailsTestSchema,
    GetUserDetailsResponseTestSchema,
    GetAccountDetailsResponseTestSchema
)
from tests.tools.logger import get_test_logger

logger = get_test_logger("GATEWAY_ASSERTIONS")


@allure.step("Check Gateway error response: {expected_status}, {expected_detail}")
def assert_gateway_error_response(
        actual: Response, *, expected_status: HTTPStatus, expected_detail: str,
) -> None:
    """Проверяет статус и причину ошибки зависимости в ответе Gateway.

    Статус проверяется до JSON. Причина ищется внутри строкового detail,
    поскольку Gateway добавляет к ответу зависимости контекст вызова.

    Args:
        actual: Сырой ответ raw-метода Gateway HTTP-клиента.
        expected_status: Ожидаемый HTTP-статус моделируемой ошибки.
        expected_detail: Причина из подготовки сценария, включая ID при not-found.

    Raises:
        AssertionError: Если статус, тип detail или причина не соответствуют ожиданию.
    """
    assert_status_code(actual.status_code, expected_status)
    assert_string_contains(actual.json()["detail"], expected_detail, "Gateway error detail")


@allure.step("Check Gateway not-found response: {expected_detail}")
def assert_gateway_not_found_response(actual: Response, *, expected_detail: str) -> None:
    """Проверяет передачу Gateway смоделированной ошибки зависимости.

    Статус проверяется до разбора JSON. Причина ищется внутри detail, поскольку
    Gateway добавляет к ней контекст вызова зависимого сервиса.

    Args:
        actual: Сырой ответ raw-метода Gateway HTTP-клиента.
        expected_detail: Сформированная причина с ID из запроса, например
            Account with id <UUID> not found.

    Raises:
        AssertionError: Если статус, тип detail или причина не соответствуют ожиданию.
    """
    assert_gateway_error_response(
        actual, expected_status=HTTPStatus.NOT_FOUND, expected_detail=expected_detail,
    )


@allure.step("Check user details")
def assert_user_details(actual: UserDetailsTestSchema, expected: UserDetailsTestSchema) -> None:
    """Сравнивает пользователя и состав его счетов независимо от порядка.

    Args:
        actual: Полученный агрегат пользователя и счетов.
        expected: Независимо подготовленные поля пользователя и ожидаемые счета.
    """
    logger.info("Check user details")
    assert_user(actual.user, expected.user)
    assert_equal(len(actual.accounts), len(expected.accounts), "accounts count")
    accounts_by_id = {account.id: account for account in actual.accounts}
    expected_account_ids = {account.id for account in expected.accounts}
    assert_equal(len(accounts_by_id), len(actual.accounts), "unique account ids")
    assert_equal(set(accounts_by_id), expected_account_ids, "account ids")
    for account in expected.accounts:
        assert_account(accounts_by_id[account.id], account)


@allure.step("Check account details")
def assert_account_details(actual: AccountDetailsTestSchema, expected: AccountDetailsTestSchema) -> None:
    """Сравнивает счёт и состав его карт независимо от порядка.

    Args:
        actual: Полученный агрегат счёта и карт.
        expected: Независимо подготовленные поля счёта и ожидаемые карты.
    """
    logger.info("Check account details")
    assert_account(actual.account, expected.account)
    assert_equal(len(actual.cards), len(expected.cards), "cards count")
    cards_by_id = {card.id: card for card in actual.cards}
    expected_card_ids = {card.id for card in expected.cards}
    assert_equal(len(cards_by_id), len(actual.cards), "unique card ids")
    assert_equal(set(cards_by_id), expected_card_ids, "card ids")
    for card in expected.cards:
        assert_card(cards_by_id[card.id], card)


@allure.step("Check get user details response")
def assert_get_user_details_response(
        actual: GetUserDetailsResponseTestSchema,
        expected: GetUserDetailsResponseTestSchema
) -> None:
    """Сравнивает пользователя и ожидаемый состав его счетов в ответе Gateway.

    Args:
        actual: Разобранный успешный HTTP-ответ Gateway.
        expected: Независимо подготовленный пользователь и его счета.
    """
    logger.info("Check get user details response")
    assert_user_details(actual.details, expected.details)


@allure.step("Check get account details response")
def assert_get_account_details_response(
        actual: GetAccountDetailsResponseTestSchema,
        expected: GetAccountDetailsResponseTestSchema
) -> None:
    """Сравнивает счёт и ожидаемый состав его карт в ответе Gateway.

    Args:
        actual: Разобранный успешный HTTP-ответ Gateway.
        expected: Независимо подготовленный счёт и его карты.
    """
    logger.info("Check get account details response")

    assert_account_details(actual.details, expected.details)
