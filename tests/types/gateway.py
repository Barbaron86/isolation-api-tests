from enum import StrEnum


class GatewayTestErrorReason(StrEnum):
    """Шаблоны сообщений об отсутствующих пользователях и счетах.

    Моки и тесты подставляют запрошенный ID через str.format().
    Формат повторяет сообщения Operations и описывает поведение тестового стенда.
    """

    USER_NOT_FOUND = "User with id {user_id} not found"
    ACCOUNT_NOT_FOUND = "Account with id {account_id} not found"
