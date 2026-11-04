from enum import StrEnum


class Scenario(StrEnum):
    """Выбирает JSON-набор моков через HTTP-заголовок или gRPC metadata.

    Gateway передаёт x-test-scenario зависимостям. Набор данных подготавливается
    для конкретных операций и протоколов; наличие имени здесь не означает,
    что у каждого обработчика есть соответствующий JSON-файл.
    """
    USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT = "user_with_active_debit_card_account"
    USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT = "user_with_active_credit_card_account"
    USER_WITHOUT_ACCOUNTS = "user_without_accounts"
    ACCOUNT_WITHOUT_CARDS = "account_without_cards"
