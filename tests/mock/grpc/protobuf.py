"""Преобразует данные динамических сценариев в сообщения gRPC-мока."""

from contracts.services.accounts.account_pb2 import Account, AccountStatus, AccountType
from contracts.services.cards.card_pb2 import Card, CardPaymentSystem, CardStatus, CardType
from contracts.services.users.user_pb2 import User
from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.users import UserTestSchema


def to_proto_user(user: UserTestSchema) -> User:
    """Преобразует подготовленного пользователя в protobuf-модель Users.

    Args:
        user: Пользователь из зарегистрированного сценария.

    Returns:
        Сообщение со строковым UUID и данными пользователя.
    """
    return User(
        id=str(user.id),
        email=user.email,
        last_name=user.last_name,
        first_name=user.first_name,
        middle_name=user.middle_name,
        phone_number=user.phone_number,
    )


def to_proto_account(account: AccountTestSchema) -> Account:
    """Преобразует подготовленный счёт в protobuf-модель Accounts.

    Args:
        account: Счёт из зарегистрированного сценария.

    Returns:
        Сообщение со строковыми UUID и значениями protobuf enum.
    """
    return Account(
        id=str(account.id),
        type=AccountType.Value(f"ACCOUNT_TYPE_{account.type.value}"),
        status=AccountStatus.Value(f"ACCOUNT_STATUS_{account.status.value}"),
        user_id=str(account.user_id),
        balance=account.balance,
    )


def to_proto_card(card: CardTestSchema) -> Card:
    """Преобразует подготовленную карту в protobuf-модель Cards.

    Args:
        card: Карта из зарегистрированного сценария.

    Returns:
        Сообщение со строковыми реквизитами и датой в формате ISO.
    """
    return Card(
        id=str(card.id),
        pin=card.pin,
        cvv=card.cvv,
        type=CardType.Value(f"CARD_TYPE_{card.type.value}"),
        status=CardStatus.Value(f"CARD_STATUS_{card.status.value}"),
        account_id=str(card.account_id),
        card_number=card.card_number,
        card_holder=card.card_holder,
        expiry_date=card.expiry_date.isoformat(),
        payment_system=CardPaymentSystem.Value(f"CARD_PAYMENT_SYSTEM_{card.payment_system.value}"),
    )
