from typing import Protocol, Self

from pydantic import BaseModel, model_validator

from tests.schema.accounts import AccountTestSchema
from tests.schema.cards import CardTestSchema
from tests.schema.mock_gateway import GatewayMockOperation, GatewayMockScenarioTestSchema
from tests.schema.users import UserTestSchema


class ScenarioPayload(BaseModel):
    """Данные одиночной карты, счёта с картами или зависимостей Gateway."""

    card: CardTestSchema | None = None
    account: AccountTestSchema | None = None
    cards: list[CardTestSchema] | None = None
    gateway: GatewayMockScenarioTestSchema | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> Self:
        """Проверяет форму набора и принадлежность карт указанному счёту.

        Returns:
            Проверенный набор данных сценария.

        Raises:
            ValueError: Если смешаны формы набора, карта относится к чужому
                счёту или повторяется её ID.
        """
        if self.gateway is not None:
            if self.card is not None or self.account is not None or self.cards is not None:
                raise ValueError("Gateway data must be provided on its own")
            return self
        if self.card is not None and self.account is None and self.cards is None:
            return self
        if self.card is not None or self.account is None or self.cards is None:
            raise ValueError("Provide either card or account with cards")
        if any(card.account_id != self.account.id for card in self.cards):
            raise ValueError("Each card must belong to the scenario account")
        if len({card.id for card in self.cards}) != len(self.cards):
            raise ValueError("Card IDs must be unique within a scenario")
        return self


class DynamicScenario(ScenarioPayload):
    """Зарегистрированный набор с идентификатором для X-Test-Scenario."""

    id: str

    @property
    def available_users(self) -> list[UserTestSchema]:
        """Возвращает пользователей, зарегистрированных для этого сценария."""
        return self.gateway.users if self.gateway is not None else []

    @property
    def available_cards(self) -> list[CardTestSchema]:
        """Возвращает карты независимо от формы зарегистрированного набора."""
        if self.gateway is not None:
            return self.gateway.cards
        if self.card is not None:
            return [self.card]
        return self.cards or []

    @property
    def available_accounts(self) -> list[AccountTestSchema]:
        """Возвращает счета независимо от формы зарегистрированного набора."""
        if self.gateway is not None:
            return self.gateway.accounts
        return [self.account] if self.account is not None else []

    def is_unavailable(self, operation: GatewayMockOperation) -> bool:
        """Определяет, задан ли сбой выбранной операции.

        Args:
            operation: Операция, которую вызвал Gateway.

        Returns:
            Признак того, что операция должна сообщить о недоступности.
        """
        return self.gateway is not None and operation in self.gateway.unavailable


class ScenarioStore(Protocol):
    """Описывает операции Admin API и выбора динамического сценария."""

    async def save(self, scenario: DynamicScenario) -> None:
        """Сохраняет сценарий по выданному идентификатору."""
        ...

    async def get(self, scenario_id: str) -> DynamicScenario | None:
        """Возвращает сценарий по ID или None при его отсутствии."""
        ...

    async def delete(self, scenario_id: str) -> None:
        """Удаляет только указанный сценарий и допускает повторный вызов."""
        ...


class InMemoryScenarioStore:
    """Хранит динамические сценарии одного экземпляра HTTP-мока."""

    def __init__(self) -> None:
        self._scenarios: dict[str, DynamicScenario] = {}

    async def save(self, scenario: DynamicScenario) -> None:
        """Сохраняет сценарий по выданному идентификатору.

        Args:
            scenario: Набор данных с уникальным ID.
        """
        self._scenarios[scenario.id] = scenario

    async def get(self, scenario_id: str) -> DynamicScenario | None:
        """Возвращает сценарий по ID или None, если он отсутствует.

        Args:
            scenario_id: Идентификатор зарегистрированного набора.
        """
        return self._scenarios.get(scenario_id)

    async def delete(self, scenario_id: str) -> None:
        """Удаляет сценарий по ID и допускает повторное удаление.

        Args:
            scenario_id: Идентификатор удаляемого набора.
        """
        self._scenarios.pop(scenario_id, None)
