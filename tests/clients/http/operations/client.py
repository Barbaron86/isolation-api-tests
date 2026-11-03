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
from tests.tools.operations_waiter import wait_for_operations_count
from tests.tools.routes import APITestRoutes


class OperationsHTTPTestClient(HTTPTestClient):
    """Читает Operations API и явно ожидает асинхронный результат."""

    @allure.step("Get operations View")
    def get_operations_api(
            self,
            query: GetOperationsQueryTestSchema,
            *,
            timeout: float | None = None,
    ) -> Response:
        """Выполняет один запрос списка операций без разбора ответа.

        Args:
            query: Фильтры списка операций.
            timeout: Лимит сетевых фаз HTTPX; None сохраняет настройку клиента.

        Returns:
            Необработанный HTTP-ответ.
        """
        return self.get(
            url=f"{APITestRoutes.OPERATIONS}",
            params=QueryParams(
                **query.model_dump(by_alias=True, exclude_none=True)
            ),
            timeout=timeout,
        )

    @allure.step("Get operation view")
    def get_operation_api(
            self,
            operation_id: UUID
    ) -> Response:
        """Выполняет один HTTP-запрос операции без разбора ответа.

        Args:
            operation_id: Первичный ключ запрашиваемой операции.

        Returns:
            Необработанный HTTP-ответ для протокольных проверок.
        """
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
            account_id: UUID | None = None,
            *,
            timeout: float | None = None,
    ) -> GetOperationsResponseTestSchema:
        """Получает список операций с проверкой HTTP-статуса и модели ответа.

        Args:
            user_id: Пользователь, операции которого запрашиваются.
            card_id: Дополнительный фильтр карты. При None не передаётся.
            account_id: Дополнительный фильтр счёта. При None не передаётся.
            timeout: Лимит сетевых фаз HTTPX в секундах; None сохраняет
                настроенный timeout клиента. Метод выполняет один запрос.

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
            ),
            timeout=timeout,
        )
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetOperationsResponseTestSchema.model_validate_json(response.text)

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
    ) -> GetOperationsResponseTestSchema:
        """Ожидает точное количество операций, повторяя только неполный результат.

        HTTPX ограничивает отдельные сетевые фазы оставшимся временем, а не
        полную длительность запроса. Непрерывно поступающее тело может пересечь
        общий срок; такой поздний ответ не принимается как успешное ожидание.

        Args:
            user_id: Пользователь, операции которого ожидаются.
            card_id: Необязательный фильтр карты.
            account_id: Необязательный фильтр счёта.
            expected_count: Точное неотрицательное целое число операций;
                bool не допускается.
            timeout: Общий срок наблюдения в секундах; None использует настройку.
            interval: Интервал опроса в секундах; None использует настройку.

        Returns:
            Проверенная модель ответа с ожидаемым количеством операций.

        Raises:
            ValueError: Если количество или параметры времени недопустимы.
            TimeoutError: Если нужный результат не наблюдался до срока.
            AssertionError: При лишних строках или неожиданном HTTP-статусе.
            pydantic.ValidationError: При нарушении схемы ответа.
            httpx.HTTPError: При транспортной ошибке без повторного запроса.
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


def build_operations_http_test_client() -> OperationsHTTPTestClient:
    """Создаёт Operations-клиент с настроенным HTTPX-клиентом.

    Returns:
        Обёртка; закрытие HTTPX-клиента выполняет владеющая фикстура.
    """
    client = build_http_test_client(
        logger=get_test_logger("OPERATION_HTTP_TEST_CLIENT"),
        config=test_settings.operations_http_client
    )
    return OperationsHTTPTestClient(client=client)
