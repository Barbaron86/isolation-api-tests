from datetime import date
from uuid import UUID

from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.users import UserTestSchema
from tests.tools.fakers import fake
from tests.types.accounts import AccountTestStatus, AccountTestType
from tests.types.cards import CardTestPaymentSystem, CardTestStatus, CardTestType


def make_user(
    *,
    email: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    middle_name: str | None = None,
    phone_number: str | None = None,
) -> UserTestSchema:
    """Создаёт пользователя с новым UUID и синтетическими контактами.

    Args:
        email: Email для сценария. По умолчанию строится из UUID на example.com.
        first_name: Имя. По умолчанию генерируется Faker.
        last_name: Фамилия. По умолчанию генерируется Faker.
        middle_name: Отчество. По умолчанию генерируется Faker.
        phone_number: Номер телефона. По умолчанию генерируется Faker.

    Returns:
        Готовая модель пользователя для динамического сценария.
    """
    user_id = fake.uuid()
    return UserTestSchema(
        id=user_id,
        email=f"{user_id}@example.com" if email is None else email,
        first_name=fake.faker.first_name() if first_name is None else first_name,
        last_name=fake.faker.last_name() if last_name is None else last_name,
        middle_name=fake.faker.first_name() if middle_name is None else middle_name,
        phone_number=fake.faker.numerify("+79#########") if phone_number is None else phone_number,
    )


def make_account(
    *,
    user_id: UUID,
    account_type: AccountTestType = AccountTestType.DEBIT_CARD,
    status: AccountTestStatus = AccountTestStatus.ACTIVE,
    balance: float = 1000.0,
) -> AccountTestSchema:
    """Создаёт счёт с новым UUID для указанного владельца.

    Args:
        user_id: ID владельца счёта.
        account_type: Тип счёта.
        status: Статус счёта.
        balance: Остаток, который должен вернуть API.

    Returns:
        Готовая модель счёта с указанным владельцем.
    """
    return AccountTestSchema(
        id=fake.uuid(), type=account_type, status=status, user_id=user_id, balance=balance,
    )


def make_card(
    *,
    account_id: UUID,
    card_type: CardTestType = CardTestType.VIRTUAL,
    status: CardTestStatus = CardTestStatus.ACTIVE,
    payment_system: CardTestPaymentSystem = CardTestPaymentSystem.VISA,
    card_holder: str = "TEST CARDHOLDER",
    expiry_date: date = date(2035, 12, 31),
) -> CardTestSchema:
    """Создаёт синтетическую карту с новым UUID для указанного счёта.

    Args:
        account_id: ID счёта карты.
        card_type: Тип карты.
        status: Статус карты.
        payment_system: Платёжная система карты.
        card_holder: Имя держателя карты.
        expiry_date: Дата окончания срока действия.

    Returns:
        Готовая модель карты с синтетическим номером, PIN и CVV.
    """
    number_type = None if payment_system == CardTestPaymentSystem.UNSPECIFIED else payment_system.value.lower()
    return CardTestSchema(
        id=fake.uuid(),
        account_id=account_id,
        type=card_type,
        status=status,
        payment_system=payment_system,
        card_holder=card_holder,
        expiry_date=expiry_date,
        card_number=fake.faker.credit_card_number(card_type=number_type),
        pin=fake.faker.numerify("####"),
        cvv=fake.faker.numerify("###"),
    )
