from uuid import UUID

import allure
import grpc

from contracts.services.operations.operations_service_pb2_grpc import OperationsServiceStub
from tests.clients.grpc.client import GRPCTestClient, build_grpc_test_channel
from tests.tools.logger import get_test_logger
from tests.tools.operations_waiter import wait_for_operations_count
from tests.config import test_settings
from contracts.services.operations.rpc_get_operation_pb2 import GetOperationRequest, GetOperationResponse
from contracts.services.operations.rpc_get_operations_pb2 import GetOperationsRequest, GetOperationsResponse


class OperationsGRPCTestClient(GRPCTestClient):
    """Читает Operations gRPC API и явно ожидает асинхронный результат."""

    def __init__(self, channel: grpc.Channel):
        """Связывает канал с Operations stub.

        Args:
            channel: Канал, который закрывает владеющая клиентом фикстура.
        """
        super().__init__(channel)

        self.stub = OperationsServiceStub(channel)

    def get_operation_api(self, request: GetOperationRequest) -> GetOperationResponse:
        """Выполняет один RPC получения операции без дополнительных проверок.

        Args:
            request: Подготовленный protobuf-запрос с ID операции.

        Returns:
            Исходный protobuf-ответ Operations.
        """
        return self.stub.GetOperation(request)

    def get_operations_api(
            self,
            request: GetOperationsRequest,
            *,
            timeout: float | None = None,
    ) -> GetOperationsResponse:
        """Выполняет один RPC со специальным сроком при его передаче.

        Args:
            request: Запрос списка операций.
            timeout: Срок RPC в секундах; None сохраняет прежний вызов без срока.

        Returns:
            Ответ Operations gRPC API.
        """
        if timeout is None:
            return self.stub.GetOperations(request)
        return self.stub.GetOperations(request, timeout=timeout)

    def get_operation(self, operation_id: UUID) -> GetOperationResponse:
        """Собирает запрос по UUID и возвращает ответ одного RPC.

        Args:
            operation_id: Первичный ключ запрашиваемой операции.

        Returns:
            Ответ с операцией; ошибки RPC передаются вызывающему коду.
        """
        request = GetOperationRequest(id=str(operation_id))
        return self.get_operation_api(request)

    def get_operations(
            self,
            user_id: UUID,
            card_id: UUID | None = None,
            account_id: UUID | None = None,
            *,
            timeout: float | None = None,
    ) -> GetOperationsResponse:
        """Выполняет однократное чтение списка с заданными фильтрами.

        Args:
            user_id: Пользователь, операции которого запрашиваются.
            card_id: Фильтр карты; при None поле не заполняется.
            account_id: Фильтр счёта; при None поле не заполняется.
            timeout: Срок одного RPC в секундах; None сохраняет вызов без
                явного срока. Метод не повторяет запрос при ошибке.

        Returns:
            Ответ Operations без повторных запросов.
        """
        request = GetOperationsRequest(user_id=str(user_id))
        if card_id is not None:
            request.card_id = str(card_id)
        if account_id is not None:
            request.account_id = str(account_id)
        return self.get_operations_api(request, timeout=timeout)

    @allure.step("Wait for {expected_count} operations: user_id={user_id}")
    def wait_for_operations(
            self,
            user_id: UUID,
            card_id: UUID | None = None,
            account_id: UUID | None = None,
            *,
            expected_count: int,
            timeout: float | None = None,
            interval: float | None = None,
    ) -> GetOperationsResponse:
        """Ожидает точное количество операций с ограниченным сроком каждого RPC.

        Args:
            user_id: Пользователь, операции которого ожидаются.
            card_id: Необязательный фильтр карты.
            account_id: Необязательный фильтр счёта.
            expected_count: Точное неотрицательное целое число операций;
                bool не допускается.
            timeout: Общий срок наблюдения в секундах; None использует настройку.
            interval: Интервал опроса в секундах; None использует настройку.

        Returns:
            Ответ gRPC API с ожидаемым количеством операций.

        Raises:
            ValueError: Если количество или параметры времени недопустимы.
            TimeoutError: Если нужный результат не наблюдался до срока.
            AssertionError: Если API вернул лишние операции.
            grpc.RpcError: При ошибке RPC без повторного запроса.
        """
        return wait_for_operations_count(
            lambda remaining: self.get_operations(
                user_id=user_id, card_id=card_id, account_id=account_id, timeout=remaining,
            ),
            expected_count=expected_count,
            description=f"user_id={user_id}, card_id={card_id}, account_id={account_id}",
            timeout=timeout,
            interval=interval,
        )


def build_operations_grpc_test_client() -> OperationsGRPCTestClient:
    """Создаёт Operations-клиент с отдельным gRPC-каналом.

    Returns:
        Клиент; закрытие канала выполняет владеющая им фикстура.
    """
    channel = build_grpc_test_channel(
        logger=get_test_logger("OPERATIONS_GRPC_TEST_CLIENT"),
        config=test_settings.operations_grpc_client
    )
    return OperationsGRPCTestClient(channel=channel)
