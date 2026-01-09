from enum import StrEnum


class APIRoutes(StrEnum):
    USERS = '/api/v1/users'
    CARDS = '/api/v1/cards'
    GATEWAY = '/api/v1/gateway'
    ACCOUNTS = '/api/v1/accounts'
    OPERATIONS = '/api/v1/operations'

    def as_tag(self) -> str:
        return self.replace('/api/v1/', '')
