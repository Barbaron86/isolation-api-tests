"""Независимые ожидания для HTTP-сценариев Gateway."""

from datetime import date
from uuid import UUID

from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.gateway import (
    AccountDetailsTestSchema,
    GetAccountDetailsResponseTestSchema,
    GetUserDetailsResponseTestSchema,
    UserDetailsTestSchema,
)
from tests.schema.users import UserTestSchema
from tests.types.accounts import AccountTestStatus, AccountTestType
from tests.types.cards import CardTestPaymentSystem, CardTestStatus, CardTestType


def expected_active_credit_user_details(*, user_id: UUID) -> GetUserDetailsResponseTestSchema:
    """Готовит пользователя с активным кредитным счётом.

    Args:
        user_id: ID запрошенного пользователя из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetUserDetailsResponseTestSchema(
        details=UserDetailsTestSchema(
            user=UserTestSchema(
                id=user_id,
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
                    user_id=user_id,
                    balance=-15230.75,
                )
            ],
        )
    )


def expected_active_debit_account_details(*, account_id: UUID) -> GetAccountDetailsResponseTestSchema:
    """Готовит активный дебетовый счёт и две его карты.

    Args:
        account_id: ID запрошенного счёта из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetAccountDetailsResponseTestSchema(
        details=AccountDetailsTestSchema(
            account=AccountTestSchema(
                id=account_id,
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
                    account_id=account_id,
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
                    account_id=account_id,
                    card_number="5500000000000004",
                    card_holder="IVAN PETROV",
                    expiry_date=date(2028, 6, 30),
                    payment_system=CardTestPaymentSystem.MASTERCARD,
                ),
            ],
        )
    )


def expected_user_details_without_accounts(*, user_id: UUID) -> GetUserDetailsResponseTestSchema:
    """Готовит пользователя с пустым списком счетов.

    Args:
        user_id: ID запрошенного пользователя из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetUserDetailsResponseTestSchema(
        details=UserDetailsTestSchema(
            user=UserTestSchema(
                id=user_id,
                email="pavel.smirnov@example.com",
                last_name="Смирнов",
                first_name="Павел",
                middle_name="Олегович",
                phone_number="+79001112233",
            ),
            accounts=[],
        )
    )


def expected_account_details_without_cards(*, account_id: UUID) -> GetAccountDetailsResponseTestSchema:
    """Готовит счёт с пустым списком карт.

    Args:
        account_id: ID запрошенного счёта из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetAccountDetailsResponseTestSchema(
        details=AccountDetailsTestSchema(
            account=AccountTestSchema(
                id=account_id,
                type=AccountTestType.DEBIT_CARD,
                status=AccountTestStatus.ACTIVE,
                user_id="e8a351ec-3c79-46b4-a152-95b0aac90d3f",
                balance=2500.5,
            ),
            cards=[],
        )
    )


def expected_user_details_with_multiple_accounts(*, user_id: UUID) -> GetUserDetailsResponseTestSchema:
    """Готовит пользователя и два его счёта.

    Args:
        user_id: ID запрошенного пользователя из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetUserDetailsResponseTestSchema(
        details=UserDetailsTestSchema(
            user=UserTestSchema(
                id=user_id,
                email="maria.orlova@example.com",
                last_name="Орлова",
                first_name="Мария",
                middle_name="Сергеевна",
                phone_number="+79002223344",
            ),
            accounts=[
                AccountTestSchema(
                    id="7f86a8d5-2d3e-4e16-99ef-b06c53f4ea41",
                    type=AccountTestType.DEBIT_CARD,
                    status=AccountTestStatus.ACTIVE,
                    user_id=user_id,
                    balance=1200.5,
                ),
                AccountTestSchema(
                    id="c194ea82-e487-4c80-b9a4-42f6ed4ed822",
                    type=AccountTestType.CREDIT_CARD,
                    status=AccountTestStatus.ACTIVE,
                    user_id=user_id,
                    balance=-3500.75,
                ),
            ],
        )
    )


def expected_account_details_with_mixed_cards(*, account_id: UUID, user_id: UUID) -> GetAccountDetailsResponseTestSchema:
    """Готовит запрошенный счёт и две принадлежащие ему карты.

    Args:
        account_id: ID запрошенного счёта из статического сценария.
        user_id: ID владельца счёта из статического сценария.

    Returns:
        Ожидаемая модель HTTP-ответа Gateway.
    """
    return GetAccountDetailsResponseTestSchema(
        details=AccountDetailsTestSchema(
            account=AccountTestSchema(
                id=account_id,
                type=AccountTestType.DEBIT_CARD,
                status=AccountTestStatus.ACTIVE,
                user_id=user_id,
                balance=1200.5,
            ),
            cards=[
                CardTestSchema(
                    id="ea6c9b9b-0bb8-4c67-b001-760b59cf907c",
                    pin="1234",
                    cvv="123",
                    type=CardTestType.VIRTUAL,
                    status=CardTestStatus.ACTIVE,
                    account_id=account_id,
                    card_number="4242424242424242",
                    card_holder="MARIA ORLOVA",
                    expiry_date=date(2029, 4, 30),
                    payment_system=CardTestPaymentSystem.VISA,
                ),
                CardTestSchema(
                    id="8c3c69bc-a9f5-4819-bd84-a58c1c55d6c9",
                    pin="2345",
                    cvv="234",
                    type=CardTestType.PHYSICAL,
                    status=CardTestStatus.ACTIVE,
                    account_id=account_id,
                    card_number="5555555555554444",
                    card_holder="MARIA ORLOVA",
                    expiry_date=date(2030, 6, 30),
                    payment_system=CardTestPaymentSystem.MASTERCARD,
                ),
            ],
        )
    )
