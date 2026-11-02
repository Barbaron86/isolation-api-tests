from http import HTTPStatus
from uuid import UUID

import allure
from httpx import Response, QueryParams

from tests.assertions.http.base import assert_status_code
from tests.clients.http.client import HTTPTestClient, build_http_test_client
from tests.config import test_settings
from tests.schema.operations import GetOperationsQueryTestSchema, GetOperationResponseTestSchema, \
    GetOperationsResponseTestSchema
from tests.tools.logger import get_test_logger
from tests.tools.routes import APITestRoutes


class OperationsHTTPTestClient(HTTPTestClient):
    @allure.step("Get operations View")
    def get_operations_api(
            self,
            query: GetOperationsQueryTestSchema
    ) -> Response:
        return self.get(
            url=f"{APITestRoutes.OPERATIONS}",
            params=QueryParams(
                **query.model_dump(by_alias=True, exclude_none=True)
            )
        )

    @allure.step("Get operation view")
    def get_operation_api(
            self,
            operation_id: UUID
    ) -> Response:
        return self.get(
            url=f"{APITestRoutes.OPERATIONS}/{operation_id}",
        )

    def get_operation(self, operation_id: UUID) -> GetOperationResponseTestSchema:
        """Получает операцию и проверяет успешный ответ до разбора модели.

        Args:
            operation_id: Идентификатор запрашиваемой операции.

        Returns:
            Проверенная модель ответа с операцией.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_operation_api(operation_id=operation_id)
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetOperationResponseTestSchema.model_validate_json(response.text)

    def get_operations(
            self,
            user_id: UUID,
            card_id: UUID | None = None,
            account_id: UUID | None = None
    ) -> GetOperationsResponseTestSchema:
        """Получает список операций с проверкой HTTP-статуса и модели ответа.

        Args:
            user_id: Пользователь, операции которого запрашиваются.
            card_id: Дополнительный фильтр карты. При None не передаётся.
            account_id: Дополнительный фильтр счёта. При None не передаётся.

        Returns:
            Проверенная модель ответа со списком операций.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_operations_api(
            query=GetOperationsQueryTestSchema(
                user_id=user_id,
                card_id=card_id,
                account_id=account_id
            )

        )
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetOperationsResponseTestSchema.model_validate_json(response.text)


def build_operations_http_test_client() -> OperationsHTTPTestClient:
    client = build_http_test_client(
        logger=get_test_logger("OPERATION_HTTP_TEST_CLIENT"),
        config=test_settings.operations_http_client
    )
    return OperationsHTTPTestClient(client=client)
