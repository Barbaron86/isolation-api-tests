"""Различимые события покупок для проверки полного маршрута Kafka → Operations."""

from datetime import datetime

import pytest

from tests.schema.operations import OperationEventTestSchema
from tests.tools.fakers import fake
from tests.types.operations import OperationTestStatus, OperationTestType


@pytest.fixture
def same_user_purchase_events() -> tuple[OperationEventTestSchema, OperationEventTestSchema]:
    """Готовит две покупки одного пользователя с разными картами и общим счётом.

    Returns:
        Независимые события IN_PROGRESS и COMPLETED с различимыми полями.
        Фикстура только создаёт данные; публикация остаётся явным действием теста.
    """
    first_event = OperationEventTestSchema(
        type=OperationTestType.PURCHASE,
        status=OperationTestStatus.IN_PROGRESS,
        amount=101.0,
        category="supermarkets",
        created_at=datetime(2026, 1, 15, 10, 0, 0),
    )
    second_event = OperationEventTestSchema(
        type=OperationTestType.PURCHASE,
        status=OperationTestStatus.COMPLETED,
        amount=202.0,
        user_id=first_event.user_id,
        account_id=first_event.account_id,
        category="taxi",
        created_at=datetime(2026, 1, 15, 10, 1, 0),
    )
    return first_event, second_event


@pytest.fixture
def different_user_purchase_events(
    same_user_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
) -> tuple[OperationEventTestSchema, OperationEventTestSchema]:
    """Готовит покупки двух пользователей с разными картами и счетами.

    Args:
        same_user_purchase_events: Базовая пара с различимыми полями покупки.

    Returns:
        Пара событий с независимыми идентификаторами владельцев.
    """
    first_event, second_event = same_user_purchase_events
    return first_event, second_event.model_copy(
        update={"user_id": fake.uuid(), "account_id": fake.uuid()},
    )


@pytest.fixture
def different_account_purchase_events(
    same_user_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
) -> tuple[OperationEventTestSchema, OperationEventTestSchema]:
    """Готовит покупки одного пользователя на разных счетах и картах.

    Args:
        same_user_purchase_events: Базовая пара покупок одного пользователя.

    Returns:
        Пара событий, из которой фильтр счёта должен выбрать одну операцию.
    """
    first_event, second_event = same_user_purchase_events
    return first_event, second_event.model_copy(update={"account_id": fake.uuid()})
