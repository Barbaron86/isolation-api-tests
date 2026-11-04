from datetime import date
from http import HTTPStatus
from uuid import UUID

import allure
from httpx import Response

from tests.assertions.base import assert_equal, assert_string_contains
from tests.assertions.http.base import assert_status_code
from tests.assertions.http.accounts import assert_account
from tests.assertions.http.cards import assert_card
from tests.assertions.http.users import assert_user
from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.gateway import (
    UserDetailsTestSchema,
    AccountDetailsTestSchema,
    GetUserDetailsResponseTestSchema,
    GetAccountDetailsResponseTestSchema
)
from tests.schema.users import UserTestSchema
from tests.tools.logger import get_test_logger
from tests.types.accounts import AccountTestType, AccountTestStatus
from tests.types.cards import CardTestPaymentSystem, CardTestStatus, CardTestType

logger = get_test_logger("GATEWAY_ASSERTIONS")




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
    assert_status_code(actual.status_code, HTTPStatus.NOT_FOUND)
    assert_string_contains(actual.json()["detail"], expected_detail, "Gateway error detail")


@allure.step("Check user details")
def assert_user_details(actual: UserDetailsTestSchema, expected: UserDetailsTestSchema) -> None:
    logger.info("Check user details")

    # UserDetails — агрегат верхнего уровня:
    # пользователь + связанные с ним счета.
    #
    # Проверка строится композиционно:
    # сначала проверяется пользователь как отдельная доменная сущность,
    # затем — список счетов.
    #
    # Такой порядок отражает бизнес-смысл данных,
    # а не случайную структуру JSON-ответа.
    assert_user(actual.user, expected.user)

    # Количество счетов — часть контракта сценария.
    # Мы явно фиксируем ожидание по длине списка,
    # чтобы не "молча" пройти лишние или недостающие элементы.
    assert_equal(len(actual.accounts), len(expected.accounts), "accounts count")

    # Далее мы проходимся по списку счетов циклом.
    #
    # Это допустимо и безопасно в рамках курса,
    # потому что:
    # - данные приходят из сценарных моков;
    # - набор счетов детерминирован и фиксирован;
    # - порядок элементов стабилен и не флакает.
    #
    # В реальных системах с нефиксированным порядком
    # здесь потребовалась бы сортировка или матчинг по ключам,
    # но в изоляционном контуре курса это сознательно не нужно.
    for index, account in enumerate(expected.accounts):
        assert_account(actual.accounts[index], account)


@allure.step("Check account details")
def assert_account_details(actual: AccountDetailsTestSchema, expected: AccountDetailsTestSchema) -> None:
    logger.info("Check account details")

    # AccountDetails — агрегат:
    # счёт + связанные с ним карты.
    #
    # Проверка начинается с базовой сущности счёта,
    # так как именно она задаёт контекст для всех карт.
    assert_account(actual.account, expected.account)

    # Аналогично проверке счетов пользователя,
    # количество карт является частью сценарного контракта.
    assert_equal(len(actual.cards), len(expected.cards), "cards count")

    # Циклическая проверка списка карт допустима по тем же причинам:
    # - данные приходят из фиксированных моков;
    # - сценарий задаёт стабильный порядок;
    # - результат не зависит от времени или внешнего состояния.
    #
    # Это позволяет писать проверки прямо и читаемо,
    # без усложнения логики теста.
    for index, card in enumerate(expected.cards):
        assert_card(actual.cards[index], card)


@allure.step("Check get user details response")
def assert_get_user_details_response(
        actual: GetUserDetailsResponseTestSchema,
        expected: GetUserDetailsResponseTestSchema
) -> None:
    logger.info("Check get user details response")

    # Ассерт уровня HTTP-ответа.
    #
    # Здесь мы сознательно не повторяем проверки полей,
    # а делегируем их в ассерт уровня агрегата.
    # Это сохраняет иерархию проверок:
    # HTTP-ответ -> агрегат -> доменные сущности.
    assert_user_details(actual.details, expected.details)


@allure.step("Check get account details response")
def assert_get_account_details_response(
        actual: GetAccountDetailsResponseTestSchema,
        expected: GetAccountDetailsResponseTestSchema
) -> None:
    logger.info("Check get account details response")

    assert_account_details(actual.details, expected.details)


@allure.step("Check get user details response. User with active credit card account")
def assert_get_user_details_response_user_with_active_credit_card_account(
        actual: GetUserDetailsResponseTestSchema,
        *,
        expected_user_id: UUID,
) -> None:
    """Сравнивает агрегат кредитного сценария с запрошенным пользователем.

    Args:
        actual: Разобранный HTTP-ответ Gateway.
        expected_user_id: Независимый ID из подготовки теста; ожидается у
            пользователя и в поле владельца каждого подготовленного счёта.
    """
    logger.info("Check get user details response. User with active credit card account")

    expected = GetUserDetailsResponseTestSchema(
        details=UserDetailsTestSchema(
            user=UserTestSchema(
                id=expected_user_id,
                email="anna.ivanova@example.com",
                last_name="Иванова",
                first_name="Анна",
                middle_name="Алексеевна",
                phone_number="+79005554433",
            ),
            accounts=[
                AccountTestSchema(
                    id="99999999-aaaa-4bbb-8ccc-000000000001",
                    type=AccountTestType.CREDIT_CARD,
                    status=AccountTestStatus.ACTIVE,
                    user_id=expected_user_id,
                    balance=-15230.75,
                )
            ],
        )
    )
    assert_get_user_details_response(actual, expected)


@allure.step("Check get account details response. User with active debit card account")
def assert_get_account_details_response_user_with_active_debit_card_account(
        actual: GetAccountDetailsResponseTestSchema,
        *,
        expected_account_id: UUID,
) -> None:
    """Сравнивает агрегат дебетового сценария с запрошенным счётом.

    Args:
        actual: Разобранный HTTP-ответ Gateway.
        expected_account_id: Независимый ID из подготовки теста; ожидается у
            счёта и в поле привязки каждой подготовленной карты.
    """
    logger.info("Check get account details response. User with active debit card account")

    expected = GetAccountDetailsResponseTestSchema(
        details=AccountDetailsTestSchema(
            account=AccountTestSchema(
                id=expected_account_id,
                type=AccountTestType.DEBIT_CARD,
                status=AccountTestStatus.ACTIVE,
                user_id="8b0e7c2a-1b6a-4e5d-9f1a-1b3f2a7c9e21",
                balance=-15230.75,
            ),
            cards=[
                CardTestSchema(
                    id="11111111-aaaa-4bbb-8ccc-222222222222",
                    pin="1234",
                    cvv="456",
                    type=CardTestType.VIRTUAL,
                    status=CardTestStatus.ACTIVE,
                    account_id=expected_account_id,
                    card_number="4111111111111111",
                    card_holder="IVAN PETROV",
                    expiry_date=date(2027, 12, 31),
                    payment_system=CardTestPaymentSystem.VISA,
                ),
                CardTestSchema(
                    id="33333333-dddd-4eee-8fff-444444444444",
                    pin="9876",
                    cvv="789",
                    type=CardTestType.PHYSICAL,
                    status=CardTestStatus.ACTIVE,
                    account_id=expected_account_id,
                    card_number="5500000000000004",
                    card_holder="IVAN PETROV",
                    expiry_date=date(2028, 6, 30),
                    payment_system=CardTestPaymentSystem.MASTERCARD,
                ),
            ],
        )
    )
    assert_get_account_details_response(actual, expected)


@allure.step("Check get user details response. User without accounts")
def assert_get_user_details_response_user_without_accounts(
        actual: GetUserDetailsResponseTestSchema,
        *,
        expected_user_id: UUID,
) -> None:
    """Проверяет пользователя сценария и отсутствие связанных счетов.

    Args:
        actual: Разобранный успешный HTTP-ответ Gateway.
        expected_user_id: ID из подготовки, с которым тест запросил пользователя.
    """
    expected = GetUserDetailsResponseTestSchema(
        details=UserDetailsTestSchema(
            user=UserTestSchema(
                id=expected_user_id,
                email="pavel.smirnov@example.com",
                last_name="Смирнов",
                first_name="Павел",
                middle_name="Олегович",
                phone_number="+79001112233",
            ),
            accounts=[],
        )
    )
    assert_get_user_details_response(actual, expected)


@allure.step("Check get account details response. Account without cards")
def assert_get_account_details_response_account_without_cards(
        actual: GetAccountDetailsResponseTestSchema,
        *,
        expected_account_id: UUID,
) -> None:
    """Проверяет счёт сценария и отсутствие привязанных карт.

    Args:
        actual: Разобранный успешный HTTP-ответ Gateway.
        expected_account_id: ID из подготовки, с которым тест запросил счёт.
    """
    expected = GetAccountDetailsResponseTestSchema(
        details=AccountDetailsTestSchema(
            account=AccountTestSchema(
                id=expected_account_id,
                type=AccountTestType.DEBIT_CARD,
                status=AccountTestStatus.ACTIVE,
                user_id="e8a351ec-3c79-46b4-a152-95b0aac90d3f",
                balance=2500.5,
            ),
            cards=[],
        )
    )
    assert_get_account_details_response(actual, expected)
