from contracts.services.accounts.account_pb2 import Account, AccountStatus, AccountType
from contracts.services.cards.card_pb2 import Card, CardPaymentSystem, CardStatus, CardType
from contracts.services.gateway.account_details_pb2 import AccountDetails
from contracts.services.gateway.rpc_get_account_details_pb2 import GetAccountDetailsResponse
from contracts.services.gateway.rpc_get_user_details_pb2 import GetUserDetailsResponse
from contracts.services.gateway.user_details_pb2 import UserDetails
from contracts.services.users.user_pb2 import User
from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.users import UserTestSchema
from tests.tools.date import to_proto_test_date


def _expected_active_debit_account(account: AccountTestSchema) -> Account:
    """Готовит ожидаемые поля активного дебетового счёта.

    Args:
        account: Данные счёта из подготовки сценария.

    Returns:
        Protobuf-счёт с ожидаемым типом и статусом.
    """
    return Account(
        id=str(account.id),
        type=AccountType.ACCOUNT_TYPE_DEBIT_CARD,
        status=AccountStatus.ACCOUNT_STATUS_ACTIVE,
        user_id=str(account.user_id),
        balance=account.balance,
    )


def expected_user_details_with_active_debit_accounts(
        *, user: UserTestSchema, accounts: list[AccountTestSchema],
) -> GetUserDetailsResponse:
    """Готовит ожидаемый gRPC-ответ с пользователем и его активными дебетовыми счетами.

    Args:
        user: Пользователь из подготовки сценария.
        accounts: Счета пользователя, которые должны войти в ответ.

    Returns:
        Ожидаемый protobuf-ответ с деталями пользователя.
    """
    return GetUserDetailsResponse(
        details=UserDetails(
            user=User(
                id=str(user.id),
                email=user.email,
                last_name=user.last_name,
                first_name=user.first_name,
                middle_name=user.middle_name,
                phone_number=user.phone_number,
            ),
            accounts=[_expected_active_debit_account(account) for account in accounts],
        ),
    )


def expected_active_debit_account_details(
        *, account: AccountTestSchema, cards: list[CardTestSchema],
) -> GetAccountDetailsResponse:
    """Готовит ожидаемый gRPC-ответ с активным дебетовым счётом и виртуальными картами Visa.

    Args:
        account: Активный дебетовый счёт из подготовки сценария.
        cards: Активные виртуальные карты Visa, которые должны войти в ответ.

    Returns:
        Ожидаемый protobuf-ответ с данными из тестового сценария.
    """
    return GetAccountDetailsResponse(
        details=AccountDetails(
            account=_expected_active_debit_account(account),
            cards=[
                Card(
                    id=str(card.id),
                    pin=card.pin,
                    cvv=card.cvv,
                    type=CardType.CARD_TYPE_VIRTUAL,
                    status=CardStatus.CARD_STATUS_ACTIVE,
                    account_id=str(card.account_id),
                    card_number=card.card_number,
                    card_holder=card.card_holder,
                    expiry_date=to_proto_test_date(card.expiry_date),
                    payment_system=CardPaymentSystem.CARD_PAYMENT_SYSTEM_VISA,
                )
                for card in cards
            ],
        ),
    )
