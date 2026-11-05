from enum import StrEnum


class GatewayTestErrorReason(StrEnum):
    """Задаёт сообщения ошибок Users, Accounts и Cards для тестовых моков.

    В шаблоны NOT_FOUND вызывающий код подставляет ID через str.format().
    Остальные значения задают причины моделируемых HTTP 503 и gRPC UNAVAILABLE.
    Это конвенция тестового стенда, а не контракт внешних сервисов.
    """

    USER_NOT_FOUND = "User with id {user_id} not found"
    ACCOUNT_NOT_FOUND = "Account with id {account_id} not found"
    USERS_SERVICE_UNAVAILABLE = "Users service unavailable"
    ACCOUNTS_SERVICE_UNAVAILABLE = "Accounts service unavailable"
    CARDS_SERVICE_UNAVAILABLE = "Cards service unavailable"
