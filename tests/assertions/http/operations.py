import allure

from tests.assertions.base import assert_equal
from tests.clients.postgres.operations.model import OperationsTestModel
from tests.schema.operations import (
    OperationTestSchema,
    OperationEventTestSchema,
    GetOperationsResponseTestSchema
)
from tests.tools.logger import get_test_logger

logger = get_test_logger("OPERATIONS_ASSERTIONS")


@allure.step("Check operation from event")
def assert_operation_from_event(
        actual: OperationTestSchema,
        expected: OperationEventTestSchema
) -> None:
    logger.info("Check operation from event")

    # Проверка операции, ожидаемые данные для которой
    # получены из события Kafka.
    #
    # Мы сравниваем только доменные атрибуты,
    # которые должны сохраниться при прохождении
    # event-driven процессинга.
    assert_equal(actual.type, expected.type, "type")
    assert_equal(actual.status, expected.status, "status")
    assert_equal(actual.amount, expected.amount, "amount")
    assert_equal(actual.user_id, expected.user_id, "user_id")
    assert_equal(actual.card_id, expected.card_id, "card_id")
    assert_equal(actual.category, expected.category, "category")
    assert_equal(actual.created_at, expected.created_at, "created_at")
    assert_equal(actual.account_id, expected.account_id, "account_id")


@allure.step("Check operation from model")
def assert_operation_from_model(
        actual: OperationTestSchema,
        expected: OperationsTestModel
) -> None:
    logger.info("Check operation from model")

    # Проверка операции, ожидаемые данные для которой
    # получены из модели базы данных.
    #
    # В этом сценарии идентификатор операции
    # является частью контракта и должен совпадать.
    assert_equal(actual.id, expected.id, "id")
    assert_equal(actual.type, expected.type, "type")
    assert_equal(actual.status, expected.status, "status")
    assert_equal(actual.amount, expected.amount, "amount")
    assert_equal(actual.user_id, expected.user_id, "user_id")
    assert_equal(actual.card_id, expected.card_id, "card_id")
    assert_equal(actual.category, expected.category, "category")
    assert_equal(actual.created_at, expected.created_at, "created_at")
    assert_equal(actual.account_id, expected.account_id, "account_id")


@allure.step("Check get operations response from events")
def assert_get_operations_response_from_events(
        actual: GetOperationsResponseTestSchema,
        expected: list[OperationEventTestSchema]
) -> None:
    logger.info("Check get operations response from events")

    assert_equal(len(actual.operations), len(expected), "operations count")
    for index, event in enumerate(expected):
        assert_operation_from_event(actual.operations[index], event)


@allure.step("Check get operations response from models")
def assert_get_operations_response_from_models(
        actual: GetOperationsResponseTestSchema,
        expected: list[OperationsTestModel]
) -> None:
    """Сравнивает полный набор операций с ORM-моделями независимо от порядка.

    Args:
        actual: Разобранный ответ HTTP API.
        expected: Подготовленные тестом операции с уникальными ID.
    """
    logger.info("Check get operations response from models")

    assert_equal(len(actual.operations), len(expected), "operations count")
    operations_by_id = {operation.id: operation for operation in actual.operations}
    expected_operation_ids = {model.id for model in expected}
    assert_equal(len(operations_by_id), len(actual.operations), "unique operation ids")
    assert_equal(set(operations_by_id), expected_operation_ids, "operation ids")
    for model in expected:
        assert_operation_from_model(operations_by_id[model.id], model)
