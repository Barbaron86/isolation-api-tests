import uuid
from http import HTTPStatus

import allure
from httpx import Response

from tests.assertions.http.base import assert_status_code
from tests.clients.http.client import HTTPTestClient, build_http_test_client
from tests.config import test_settings
from tests.context.base import DynamicScenarioContext, RequestContext
from tests.schema.gateway import (
    GetUserDetailsResponseTestSchema,
    GetAccountDetailsResponseTestSchema,
)
from tests.tools.logger import get_test_logger
from tests.tools.routes import APITestRoutes


class GatewayHTTPTestClient(HTTPTestClient):
    """Вызывает HTTP API Gateway с контекстом выбранного мок-сценария.

    Raw-методы возвращают HTTPX Response. Успешные фасады проверяют точный
    статус ответа и разбирают его в тестовую Pydantic-модель.
    """

    @allure.step("Get user details")
    def get_user_details_api(
            self,
            user_id: uuid.UUID,
            context: RequestContext | DynamicScenarioContext,
    ) -> Response:
        # Низкоуровневый метод "api" возвращает сырой Response.
        #
        # Он нужен как строительный блок: если тесту потребуется
        # отдельная диагностика статусов / заголовков / raw текста,
        # это можно сделать на уровне Response.
        #
        # Важно: context обязателен, потому что эти ручки gateway
        # в рамках изоляционных тестов управляются сценарием.
        return self.get(
            f"{APITestRoutes.GATEWAY}/user-details/{user_id}",
            context=context,
        )

    @allure.step("Get account details")
    def get_account_details_api(
            self,
            account_id: uuid.UUID,
            context: RequestContext | DynamicScenarioContext,
    ) -> Response:
        return self.get(
            f"{APITestRoutes.GATEWAY}/account-details/{account_id}",
            context=context,
        )

    def get_user_details(
            self, context: RequestContext | DynamicScenarioContext, *, user_id: uuid.UUID,
    ) -> GetUserDetailsResponseTestSchema:
        """Получает пользователя и его счета по явно переданному ID.

        Args:
            context: Сценарий, передаваемый Gateway и его зависимостям.
            user_id: ID пользователя, которого тест запрашивает у Gateway.

        Returns:
            Проверенная модель ответа с пользователем и счетами.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_user_details_api(user_id, context)
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetUserDetailsResponseTestSchema.model_validate_json(response.text)

    def get_account_details(
            self, context: RequestContext | DynamicScenarioContext, *, account_id: uuid.UUID,
    ) -> GetAccountDetailsResponseTestSchema:
        """Получает счёт и его карты по явно переданному ID.

        Args:
            context: Сценарий, передаваемый Gateway и его зависимостям.
            account_id: ID счёта, который тест запрашивает у Gateway.

        Returns:
            Проверенная модель ответа со счётом и картами.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_account_details_api(account_id, context)
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetAccountDetailsResponseTestSchema.model_validate_json(response.text)


def build_gateway_http_test_client() -> GatewayHTTPTestClient:
    """Создаёт Gateway-клиент с общим логгером запроса и ответа.

    Returns:
        Обёртка над настроенным HTTPX-клиентом Gateway.
    """
    client = build_http_test_client(
        logger=get_test_logger("GATEWAY_HTTP_TEST_CLIENT"),
        config=test_settings.gateway_http_client,
    )
    return GatewayHTTPTestClient(client=client)
