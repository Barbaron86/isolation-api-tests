from enum import StrEnum
from typing import Self

from pydantic import BaseModel, Field, model_validator

from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.users import UserTestSchema


class GatewayMockOperation(StrEnum):
    """Операции зависимостей Gateway, для которых можно задать недоступность."""

    GET_USER = "users.get_user"
    GET_ACCOUNTS = "accounts.get_accounts"
    GET_ACCOUNT = "accounts.get_account"
    GET_CARDS = "cards.get_cards"


class GatewayMockScenarioTestSchema(BaseModel):
    """Данные и сбои зависимостей одного динамического сценария Gateway.

    Attributes:
        users: Пользователи для поиска по ID.
        accounts: Счета для поиска по ID и фильтрации по владельцу.
        cards: Карты для поиска по ID и фильтрации по счёту.
        unavailable: Операции, которые сообщают о недоступности в сценарии.
    """

    users: list[UserTestSchema] = Field(default_factory=list)
    accounts: list[AccountTestSchema] = Field(default_factory=list)
    cards: list[CardTestSchema] = Field(default_factory=list)
    unavailable: list[GatewayMockOperation] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_ids(self) -> Self:
        """Проверяет уникальность ID внутри каждого списка сущностей.

        Набор может содержать только часть связанных записей.

        Returns:
            Проверенный набор сценария.

        Raises:
            ValueError: Если внутри одного списка повторяется ID.
        """
        for name, entities in (("users", self.users), ("accounts", self.accounts), ("cards", self.cards)):
            if len({entity.id for entity in entities}) != len(entities):
                raise ValueError(f"IDs in {name} must be unique within a scenario")
        return self
