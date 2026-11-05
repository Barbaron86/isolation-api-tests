from uuid import UUID

import allure
import grpc

from contracts.services.gateway.gateway_service_pb2_grpc import GatewayServiceStub
from contracts.services.gateway.rpc_get_account_details_pb2 import (
    GetAccountDetailsRequest,
    GetAccountDetailsResponse,
)
from contracts.services.gateway.rpc_get_user_details_pb2 import (
    GetUserDetailsRequest,
    GetUserDetailsResponse,
)
from tests.clients.grpc.client import GRPCTestClient, build_grpc_test_channel
from tests.config import test_settings
from tests.context.base import RequestContext, build_grpc_test_metadata
from tests.tools.logger import get_test_logger


class GatewayGRPCTestClient(GRPCTestClient):
    """Вызывает gRPC API Gateway с явными ID и контекстом мок-сценария."""

    def __init__(self, channel: grpc.Channel):
        """Создаёт Gateway stub поверх предоставленного канала.

        Args:
            channel: Канал, жизненным циклом которого управляет вызывающая сторона.
        """
        super().__init__(channel)
        self.stub = GatewayServiceStub(channel)

    def get_user_details_api(
            self,
            request: GetUserDetailsRequest,
            context: RequestContext,
    ) -> GetUserDetailsResponse:
        """Вызывает GetUserDetails с подготовленным protobuf-запросом.

        Args:
            request: Запрос с ID пользователя.
            context: Сценарий для metadata Gateway и его зависимостей.

        Returns:
            Исходный protobuf-ответ Gateway.

        Raises:
            grpc.RpcError: Если RPC завершился ошибкой.
        """
        return self.stub.GetUserDetails(
            request,
            metadata=build_grpc_test_metadata(context),
        )

    def get_account_details_api(
            self,
            request: GetAccountDetailsRequest,
            context: RequestContext,
    ) -> GetAccountDetailsResponse:
        """Вызывает GetAccountDetails с подготовленным protobuf-запросом.

        Args:
            request: Запрос с ID счёта.
            context: Сценарий для metadata Gateway и его зависимостей.

        Returns:
            Исходный protobuf-ответ Gateway.

        Raises:
            grpc.RpcError: Если RPC завершился ошибкой.
        """
        return self.stub.GetAccountDetails(
            request,
            metadata=build_grpc_test_metadata(context),
        )

    @allure.step("Get user details")
    def get_user_details(
            self, *, user_id: UUID, context: RequestContext,
    ) -> GetUserDetailsResponse:
        """Получает пользователя и его счета по явно переданному ID.

        Args:
            user_id: ID пользователя из подготовки теста.
            context: Сценарий для metadata Gateway и его зависимостей.

        Returns:
            Исходный protobuf-ответ с пользователем и счетами.

        Raises:
            grpc.RpcError: Если RPC завершился ошибкой.
        """
        request = GetUserDetailsRequest(id=str(user_id))
        return self.get_user_details_api(request, context)

    @allure.step("Get account details")
    def get_account_details(
            self, *, account_id: UUID, context: RequestContext,
    ) -> GetAccountDetailsResponse:
        """Получает счёт и его карты по явно переданному ID.

        Args:
            account_id: ID счёта из подготовки теста.
            context: Сценарий для metadata Gateway и его зависимостей.

        Returns:
            Исходный protobuf-ответ со счётом и картами.

        Raises:
            grpc.RpcError: Если RPC завершился ошибкой.
        """
        request = GetAccountDetailsRequest(id=str(account_id))
        return self.get_account_details_api(request, context)


def build_gateway_grpc_test_client() -> GatewayGRPCTestClient:
    """Создаёт Gateway-клиент с настроенным тестовым gRPC-каналом.

    Returns:
        Клиент, канал которого должна закрыть вызывающая сторона.
    """
    channel = build_grpc_test_channel(
        logger=get_test_logger("GATEWAY_GRPC_TEST_CLIENT"),
        config=test_settings.gateway_grpc_client,
    )
    return GatewayGRPCTestClient(channel=channel)
