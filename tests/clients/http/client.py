from logging import Logger

import allure
from httpx import Client, Response, QueryParams, Headers

from tests.clients.http.logger_event_hook import HTTPLoggerEventHook
from tests.context.base import DynamicScenarioContext, RequestContext, build_http_test_headers
from tests.tools.config.http import HTTPClientTestConfig


class HTTPTestClient:
    """Передаёт HTTP-запросы и тестовый контекст через настроенный HTTPX Client.

    Проверку статуса и разбор модели выполняет фасад конкретного сервиса.
    Владелец переданного HTTPX-клиента отвечает за его закрытие.
    """

    def __init__(self, client: Client) -> None:
        """Сохраняет HTTPX-клиент, созданный фабрикой тестового слоя.

        Args:
            client: Соединения и настройки HTTP; закрытие остаётся обязанностью владельца.
        """
        self.client = client

    @allure.step("Make GET request to {url}")
    def get(
            self,
            url: str,
            params: QueryParams | None = None,
            context: RequestContext | DynamicScenarioContext | None = None,
            *,
            timeout: float | None = None,
    ) -> Response:
        """Выполняет GET с контекстом и необязательным timeout фаз HTTPX.

        Args:
            url: Относительный или абсолютный адрес запроса.
            params: Query-параметры запроса.
            context: Необязательный тестовый контекст.
            timeout: Лимит отдельных сетевых фаз; None сохраняет настройку клиента.

        Returns:
            Необработанный HTTP-ответ.
        """
        headers = Headers()
        if context:
            headers = Headers(build_http_test_headers(context))
        return self.client.get(
            url=url,
            params=params,
            headers=headers,
            **({"timeout": timeout} if timeout is not None else {}),
        )


def build_http_test_client(
        logger: Logger,
        config: HTTPClientTestConfig
) -> Client:
    """Создаёт HTTPX-клиент с адресом сервиса, timeout и логированием запросов.

    Args:
        logger: Логгер для request/response event hooks HTTPX.
        config: Базовый URL и timeout отдельных сетевых фаз.

    Returns:
        Клиент для повторных запросов внутри теста. Создавший его код отвечает
        за вызов close после завершения работы.
    """

    logger_event_hook = HTTPLoggerEventHook(logger=logger)

    return Client(
        timeout=config.timeout,
        base_url=str(config.url),
        event_hooks={
            "request": [logger_event_hook.request],
            "response": [logger_event_hook.response],
        },
    )
