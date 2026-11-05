from datetime import date
from uuid import UUID

import allure
import grpc

from contracts.services.accounts.account_pb2 import Account, AccountStatus, AccountType
from contracts.services.cards.card_pb2 import Card, CardPaymentSystem, CardStatus, CardType
from contracts.services.gateway.account_details_pb2 import AccountDetails
from contracts.services.gateway.rpc_get_account_details_pb2 import GetAccountDetailsResponse
from contracts.services.gateway.rpc_get_user_details_pb2 import GetUserDetailsResponse
from contracts.services.gateway.user_details_pb2 import UserDetails
from contracts.services.users.user_pb2 import User
from tests.assertions.base import assert_equal, assert_string_contains
from tests.assertions.grpc.accounts import assert_account
from tests.assertions.grpc.cards import assert_card
from tests.assertions.grpc.users import assert_user
from tests.tools.date import to_proto_test_date
from tests.tools.logger import get_test_logger

logger = get_test_logger("GRPC_GATEWAY_ASSERTIONS")


@allure.step("Check Gateway RPC error: {expected_code}, {expected_detail}")
def assert_gateway_rpc_error(
        actual: grpc.RpcError, *, expected_code: grpc.StatusCode, expected_detail: str,
) -> None:
    """Проверяет точный gRPC-код и причину ошибки зависимости Gateway.

    Код проверяется до detail. Gateway дополняет причину контекстом вызова,
    поэтому ожидаемый текст ищется внутри строкового detail.

    Args:
        actual: Исключение от raw-метода Gateway gRPC-клиента.
        expected_code: Ожидаемый gRPC-код моделируемой ошибки.
        expected_detail: Причина из подготовки, включая ID при not-found.

    Raises:
        AssertionError: Если код, тип detail или причина не соответствуют ожиданию.
    """
    assert_equal(actual.code(), expected_code, "Gateway RPC status code")
    assert_string_contains(actual.details(), expected_detail, "Gateway RPC error detail")


@allure.step("Check user details")
def assert_user_details(actual: UserDetails, expected: UserDetails) -> None:
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
def assert_account_details(actual: AccountDetails, expected: AccountDetails) -> None:
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
        actual: GetUserDetailsResponse,
        expected: GetUserDetailsResponse
) -> None:
    """Сравнивает protobuf-ответ с независимо подготовленным агрегатом пользователя.

    Args:
        actual: Полученный protobuf-ответ Gateway.
        expected: Подготовленный ответ с ожидаемыми полями и составом счетов.
    """
    logger.info("Check get user details response")

    assert_user_details(actual.details, expected.details)


@allure.step("Check get account details response")
def assert_get_account_details_response(
        actual: GetAccountDetailsResponse,
        expected: GetAccountDetailsResponse
) -> None:
    """Сравнивает protobuf-ответ с независимо подготовленным агрегатом счёта.

    Args:
        actual: Полученный protobuf-ответ Gateway.
        expected: Подготовленный ответ с ожидаемыми полями и составом карт.
    """
    logger.info("Check get account details response")

    assert_account_details(actual.details, expected.details)


@allure.step("Check get user details response. User with active credit card account")
def assert_get_user_details_response_user_with_active_credit_card_account(
        actual: GetUserDetailsResponse,
        *,
        expected_user_id: UUID,
) -> None:
    """Сравнивает агрегат кредитного сценария с запрошенным пользователем.

    Args:
        actual: Protobuf-ответ Gateway.
        expected_user_id: Независимый ID из подготовки теста; ожидается у
            пользователя и в поле владельца каждого подготовленного счёта.
    """
    logger.info("Check get user details response. User with active credit card account")

    expected = GetUserDetailsResponse(
        details=UserDetails(
            user=User(
                id=str(expected_user_id),
                email="anna.ivanova@example.com",
                last_name="Иванова",
                first_name="Анна",
                middle_name="Алексеевна",
                phone_number="+79005554433",
            ),
            accounts=[
                Account(
                    id="99999999-aaaa-4bbb-8ccc-000000000001",
                    type=AccountType.ACCOUNT_TYPE_CREDIT_CARD,
                    status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                    user_id=str(expected_user_id),
                    balance=-15230.75,
                )
            ],
        )
    )
    assert_get_user_details_response(actual, expected)


@allure.step("Check get account details response. User with active debit card account")
def assert_get_account_details_response_user_with_active_debit_card_account(
        actual: GetAccountDetailsResponse,
        *,
        expected_account_id: UUID,
) -> None:
    """Сравнивает агрегат дебетового сценария с запрошенным счётом.

    Args:
        actual: Protobuf-ответ Gateway.
        expected_account_id: Независимый ID из подготовки теста; ожидается у
            счёта и в поле привязки каждой подготовленной карты.
    """
    logger.info("Check get account details response. User with active debit card account")

    expected = GetAccountDetailsResponse(
        details=AccountDetails(
            account=Account(
                id=str(expected_account_id),
                type=AccountType.ACCOUNT_TYPE_DEBIT_CARD,
                status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                user_id="8b0e7c2a-1b6a-4e5d-9f1a-1b3f2a7c9e21",
                balance=-15230.75,
            ),
            cards=[
                Card(
                    id="11111111-aaaa-4bbb-8ccc-222222222222",
                    pin="1234",
                    cvv="456",
                    type=CardType.CARD_TYPE_VIRTUAL,
                    status=CardStatus.CARD_STATUS_ACTIVE,
                    account_id=str(expected_account_id),
                    card_number="4111111111111111",
                    card_holder="IVAN PETROV",
                    expiry_date=to_proto_test_date(date(2027, 12, 31)),
                    payment_system=CardPaymentSystem.CARD_PAYMENT_SYSTEM_VISA,
                ),
                Card(
                    id="33333333-dddd-4eee-8fff-444444444444",
                    pin="9876",
                    cvv="789",
                    type=CardType.CARD_TYPE_PHYSICAL,
                    status=CardStatus.CARD_STATUS_ACTIVE,
                    account_id=str(expected_account_id),
                    card_number="5500000000000004",
                    card_holder="IVAN PETROV",
                    expiry_date=to_proto_test_date(date(2028, 6, 30)),
                    payment_system=CardPaymentSystem.CARD_PAYMENT_SYSTEM_MASTERCARD,
                ),
            ],
        )
    )
    assert_get_account_details_response(actual, expected)


@allure.step("Check get user details response. User without accounts")
def assert_get_user_details_response_user_without_accounts(
        actual: GetUserDetailsResponse,
        *,
        expected_user_id: UUID,
) -> None:
    """Проверяет пользователя сценария и отсутствие связанных счетов.

    Args:
        actual: Успешный protobuf-ответ Gateway.
        expected_user_id: ID из подготовки, с которым тест запросил пользователя.
    """
    expected = GetUserDetailsResponse(
        details=UserDetails(
            user=User(
                id=str(expected_user_id),
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
        actual: GetAccountDetailsResponse,
        *,
        expected_account_id: UUID,
) -> None:
    """Проверяет счёт сценария и отсутствие привязанных карт.

    Args:
        actual: Успешный protobuf-ответ Gateway.
        expected_account_id: ID из подготовки, с которым тест запросил счёт.
    """
    expected = GetAccountDetailsResponse(
        details=AccountDetails(
            account=Account(
                id=str(expected_account_id),
                type=AccountType.ACCOUNT_TYPE_DEBIT_CARD,
                status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                user_id="e8a351ec-3c79-46b4-a152-95b0aac90d3f",
                balance=2500.5,
            ),
            cards=[],
        )
    )
    assert_get_account_details_response(actual, expected)


@allure.step("Check get user details response. User with multiple accounts")
def assert_get_user_details_response_user_with_multiple_accounts(
        actual: GetUserDetailsResponse,
        *,
        expected_user_id: UUID,
) -> None:
    """Проверяет пользователя и два его счёта без записи другого владельца.

    Args:
        actual: Успешный protobuf-ответ Gateway.
        expected_user_id: ID подготовленного пользователя из запроса теста.
    """
    expected = GetUserDetailsResponse(
        details=UserDetails(
            user=User(
                id=str(expected_user_id),
                email="maria.orlova@example.com",
                last_name="Орлова",
                first_name="Мария",
                middle_name="Сергеевна",
                phone_number="+79002223344",
            ),
            accounts=[
                Account(
                    id="7f86a8d5-2d3e-4e16-99ef-b06c53f4ea41",
                    type=AccountType.ACCOUNT_TYPE_DEBIT_CARD,
                    status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                    user_id=str(expected_user_id),
                    balance=1200.5,
                ),
                Account(
                    id="c194ea82-e487-4c80-b9a4-42f6ed4ed822",
                    type=AccountType.ACCOUNT_TYPE_CREDIT_CARD,
                    status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                    user_id=str(expected_user_id),
                    balance=-3500.75,
                ),
            ],
        )
    )
    assert_get_user_details_response(actual, expected)


@allure.step("Check get account details response. Cards belong to requested account")
def assert_get_account_details_response_account_with_mixed_cards(
        actual: GetAccountDetailsResponse,
        *,
        expected_account_id: UUID,
        expected_user_id: UUID,
) -> None:
    """Проверяет счёт и его две карты без карты другого счёта.

    Args:
        actual: Успешный protobuf-ответ Gateway.
        expected_account_id: ID подготовленного счёта из запроса теста.
        expected_user_id: Независимый ID владельца подготовленного счёта.
    """
    expected = GetAccountDetailsResponse(
        details=AccountDetails(
            account=Account(
                id=str(expected_account_id),
                type=AccountType.ACCOUNT_TYPE_DEBIT_CARD,
                status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
                user_id=str(expected_user_id),
                balance=1200.5,
            ),
            cards=[
                Card(
                    id="ea6c9b9b-0bb8-4c67-b001-760b59cf907c",
                    pin="1234",
                    cvv="123",
                    type=CardType.CARD_TYPE_VIRTUAL,
                    status=CardStatus.CARD_STATUS_ACTIVE,
                    account_id=str(expected_account_id),
                    card_number="4242424242424242",
                    card_holder="MARIA ORLOVA",
                    expiry_date=to_proto_test_date(date(2029, 4, 30)),
                    payment_system=CardPaymentSystem.CARD_PAYMENT_SYSTEM_VISA,
                ),
                Card(
                    id="8c3c69bc-a9f5-4819-bd84-a58c1c55d6c9",
                    pin="2345",
                    cvv="234",
                    type=CardType.CARD_TYPE_PHYSICAL,
                    status=CardStatus.CARD_STATUS_ACTIVE,
                    account_id=str(expected_account_id),
                    card_number="5555555555554444",
                    card_holder="MARIA ORLOVA",
                    expiry_date=to_proto_test_date(date(2030, 6, 30)),
                    payment_system=CardPaymentSystem.CARD_PAYMENT_SYSTEM_MASTERCARD,
                ),
            ],
        )
    )
    assert_get_account_details_response(actual, expected)
