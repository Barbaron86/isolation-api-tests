import uuid
from http import HTTPStatus

import allure
from httpx import Response

from tests.assertions.http.base import assert_status_code
from tests.clients.http.client import HTTPTestClient, build_http_test_client
from tests.config import test_settings
from tests.context.base import RequestContext
from tests.schema.gateway import (
    GetUserDetailsResponseTestSchema,
    GetAccountDetailsResponseTestSchema,
)
from tests.tools.fakers import fake
from tests.tools.logger import get_test_logger
from tests.tools.routes import APITestRoutes


class GatewayHTTPTestClient(HTTPTestClient):
    """
    HTTP API-клиент тестового слоя для gateway-service.

    Это специализированный клиент, построенный поверх HTTPTestClient.
    Он знает HTTP-контракт gateway-service (пути и ответы), но остаётся
    тестовым инструментом, а не частью бизнес-логики системы.

    Ключевой смысл этого клиента в курсе:
    тест обращается к gateway-service, а gateway-service "под капотом"
    обращается к внешним интеграциям (users/cards/accounts),
    которые в изоляционном контуре подменены мок-сервисами.

    Поэтому входные идентификаторы (user_id / account_id) в этих вызовах
    не являются управляющим параметром поведения — поведение определяется
    сценарным контекстом (RequestContext -> x-test-scenario).
    """

    @allure.step("Get user details")
    def get_user_details_api(
            self,
            user_id: uuid.UUID,
            context: RequestContext,
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
            context: RequestContext,
    ) -> Response:
        return self.get(
            f"{APITestRoutes.GATEWAY}/account-details/{account_id}",
            context=context,
        )

    def get_user_details(self, context: RequestContext) -> GetUserDetailsResponseTestSchema:
        """Получает агрегат пользователя по сценарию с проверкой HTTP-ответа.

        Сценарные моки выбирают данные независимо от случайного ID в URL.

        Args:
            context: Сценарий, передаваемый Gateway и его зависимостям.

        Returns:
            Проверенная модель ответа с пользователем и счетами.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_user_details_api(fake.uuid(), context)
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetUserDetailsResponseTestSchema.model_validate_json(response.text)

    def get_account_details(self, context: RequestContext) -> GetAccountDetailsResponseTestSchema:
        """Получает агрегат счёта по сценарию с проверкой HTTP-ответа.

        Args:
            context: Сценарий, передаваемый Gateway и его зависимостям.

        Returns:
            Проверенная модель ответа со счётом и картами.

        Raises:
            AssertionError: Если статус ответа отличается от HTTPStatus.OK.
            pydantic.ValidationError: Если тело не соответствует модели ответа.
        """
        response = self.get_account_details_api(fake.uuid(), context)
        assert_status_code(response.status_code, HTTPStatus.OK)
        return GetAccountDetailsResponseTestSchema.model_validate_json(response.text)


def build_gateway_http_test_client() -> GatewayHTTPTestClient:
    # Фабрика строит специализированный клиент так же,
    # как и остальные клиенты тестового слоя:
    # - конфигурация берётся из test_settings,
    # - логгер создаётся единым способом,
    # - транспорт настраивается в build_http_test_client.
    #
    # Таким образом, все сервисные клиенты наследуют единое
    # поведение транспорта: base_url, timeout, event hooks, логи.
    client = build_http_test_client(
        logger=get_test_logger("GATEWAY_HTTP_TEST_CLIENT"),
        config=test_settings.gateway_http_client,
    )
    return GatewayHTTPTestClient(client=client)
