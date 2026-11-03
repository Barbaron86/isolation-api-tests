from uuid import UUID

import allure

from tests.tools.logger import get_test_logger
from tests.assertions.base import assert_equal
from tests.schema.operations import OperationEventTestSchema
from tests.clients.postgres.operations.model import OperationsTestModel
from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsResponse
from contracts.services.operations.operation_pb2 import Operation, OperationType, OperationStatus
from tests.tools.date import to_proto_test_datetime
from tests.types.operations import OperationTestType, OperationTestStatus

logger = get_test_logger("GRPC_OPERATIONS_ASSERTIONS")

OPERATION_TYPE_TO_PROTO = {
    OperationTestType.UNSPECIFIED: OperationType.OPERATION_TYPE_UNSPECIFIED,
    OperationTestType.FEE: OperationType.OPERATION_TYPE_FEE,
    OperationTestType.TOP_UP: OperationType.OPERATION_TYPE_TOP_UP,
    OperationTestType.PURCHASE: OperationType.OPERATION_TYPE_PURCHASE,
    OperationTestType.CASHBACK: OperationType.OPERATION_TYPE_CASHBACK,
    OperationTestType.TRANSFER: OperationType.OPERATION_TYPE_TRANSFER,
    OperationTestType.REVERSAL: OperationType.OPERATION_TYPE_REVERSAL,
    OperationTestType.BILL_PAYMENT: OperationType.OPERATION_TYPE_BILL_PAYMENT,
    OperationTestType.CASH_WITHDRAWAL: OperationType.OPERATION_TYPE_CASH_WITHDRAWAL,
}

OPERATION_STATUS_TO_PROTO = {
    OperationTestStatus.UNSPECIFIED: OperationStatus.OPERATION_STATUS_UNSPECIFIED,
    OperationTestStatus.IN_PROGRESS: OperationStatus.OPERATION_STATUS_IN_PROGRESS,
    OperationTestStatus.COMPLETED: OperationStatus.OPERATION_STATUS_COMPLETED,
    OperationTestStatus.REVERSED: OperationStatus.OPERATION_STATUS_REVERSED,
    OperationTestStatus.FAILED: OperationStatus.OPERATION_STATUS_FAILED,
}


@allure.step("Check operation from event")
def assert_operation_from_event(
        actual: Operation,
        expected: OperationEventTestSchema
) -> None:
    """Сравнивает поля protobuf-операции с независимым событием.

    Args:
        actual: Операция из gRPC-ответа.
        expected: Событие, отправленное тестом в Kafka.
    """
    logger.info("Check get operation from event")

    assert_equal(actual.type, OPERATION_TYPE_TO_PROTO[expected.type], "type")
    assert_equal(actual.status, OPERATION_STATUS_TO_PROTO[expected.status], "status")
    assert_equal(actual.amount, expected.amount, "amount")
    assert_equal(UUID(actual.user_id), expected.user_id, "user_id")
    assert_equal(UUID(actual.card_id), expected.card_id, "card_id")
    assert_equal(actual.category, expected.category, "category")
    assert_equal(actual.created_at, to_proto_test_datetime(expected.created_at), "created_at")
    assert_equal(UUID(actual.account_id), expected.account_id, "account_id")


@allure.step("Check operation from model")
def assert_operation_from_model(
        actual: Operation,
        expected: OperationsTestModel
) -> None:
    """Сравнивает gRPC-операцию с независимо подготовленной записью БД.

    Args:
        actual: Операция, возвращённая RPC.
        expected: Модель, сохранённая при подготовке теста.
    """
    logger.info("Check operation from model")

    assert_equal(actual.id, str(expected.id), "id")
    assert_equal(actual.type, OPERATION_TYPE_TO_PROTO[OperationTestType(expected.type)], "type")
    assert_equal(actual.status, OPERATION_STATUS_TO_PROTO[OperationTestStatus(expected.status)], "status")
    assert_equal(actual.amount, expected.amount, "amount")
    assert_equal(actual.user_id, str(expected.user_id), "user_id")
    assert_equal(actual.card_id, str(expected.card_id), "card_id")
    assert_equal(actual.account_id, str(expected.account_id), "account_id")
    assert_equal(actual.category, expected.category, "category")
    assert_equal(actual.created_at, to_proto_test_datetime(expected.created_at), "created_at")


@allure.step("Check get operations response from events")
def assert_get_operations_response_from_events(
        actual: GetOperationsResponse,
        expected: list[OperationEventTestSchema]
) -> None:
    """Сравнивает события с protobuf-операциями без зависимости от порядка.

    Args:
        actual: Ответ gRPC API со списком операций.
        expected: Отправленные события с уникальными парами пользователя и карты.
    """
    logger.info("Check get operations response from event")

    assert_equal(len(actual.operations), len(expected), "count operations")
    operations_by_key = {
        (UUID(operation.user_id), UUID(operation.card_id)): operation
        for operation in actual.operations
    }
    events_by_key = {(event.user_id, event.card_id): event for event in expected}
    assert_equal(len(operations_by_key), len(actual.operations), "unique operation keys")
    assert_equal(len(events_by_key), len(expected), "unique event keys")
    operation_ids = {UUID(operation.id) for operation in actual.operations}
    assert_equal(len(operation_ids), len(actual.operations), "unique operation ids")
    assert_equal(set(operations_by_key), set(events_by_key), "operation event keys")
    for key, event in events_by_key.items():
        assert_operation_from_event(operations_by_key[key], event)


@allure.step("Check get operations response from models")
def assert_get_operations_response_from_models(
        actual: GetOperationsResponse,
        expected: list[OperationsTestModel]
) -> None:
    """Сравнивает полный набор операций с ORM-моделями независимо от порядка.

    Args:
        actual: Ответ gRPC API со списком операций.
        expected: Подготовленные тестом операции с уникальными ID.
    """
    logger.info("Check get operations response from model")

    assert_equal(len(actual.operations), len(expected), "count operations")
    operations_by_id = {operation.id: operation for operation in actual.operations}
    expected_operation_ids = {str(model.id) for model in expected}
    assert_equal(len(operations_by_id), len(actual.operations), "unique operation ids")
    assert_equal(set(operations_by_id), expected_operation_ids, "operation ids")
    for model in expected:
        assert_operation_from_model(operations_by_id[str(model.id)], model)
