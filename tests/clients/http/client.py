from logging import Logger
from time import perf_counter

import allure
from httpx import Client, Response, QueryParams, Headers, codes

from tests.clients.http.logger_event_hook import HTTPLoggerEventHook
from tests.context.base import RequestContext, build_http_test_headers
from tests.tools.config.http import HTTPClientTestConfig
from tests.tools.logger import get_test_logger


class HTTPTestClient:
    """Передаёт HTTP-запросы и тестовый контекст через настроенный HTTPX Client.

    Проверку статуса и разбор модели выполняет фасад конкретного сервиса.
    Владелец переданного HTTPX-клиента отвечает за его закрытие.
    """

    def __init__(self, client: Client, *, logger: Logger | None = None) -> None:
        """Сохраняет HTTPX-клиент и логгер завершённых запросов.

        Args:
            client: Соединения и настройки HTTP; закрытие остаётся обязанностью владельца.
            logger: Логгер сервиса; по умолчанию общий тестовый HTTP-логгер.
        """
        self.client = client
        self._logger = logger if logger is not None else get_test_logger("HTTP_TEST_CLIENT")

    @allure.step("Make GET request to {url}")
    def get(
            self,
            url: str,
            params: QueryParams | None = None,
            context: RequestContext | None = None,
            *,
            timeout: float | None = None,
    ) -> Response:
        """Выполняет GET и записывает статус и время после чтения ответа.

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
        started_at = perf_counter()
        response = self.client.get(
            url=url,
            params=params,
            headers=headers,
            **({"timeout": timeout} if timeout is not None else {}),
        )
        duration_ms = (perf_counter() - started_at) * 1000
        request = response.request
        path = request.url.raw_path.partition(b"?")[0].decode("ascii")
        status = f"{response.status_code} {codes.get_reason_phrase(response.status_code)}".strip()
        self._logger.info(
            f"⬅️ [RESPONSE] HTTP {request.method} {path} · {status} · {duration_ms:.0f} ms"
        )
        return response


def build_http_test_client(
        logger: Logger,
        config: HTTPClientTestConfig
) -> Client:
    """Создаёт HTTPX-клиент с адресом сервиса, timeout и логированием запросов.

    Args:
        logger: Логгер отправки запросов через HTTPX event hook.
        config: Базовый URL и timeout отдельных сетевых фаз.

    Returns:
        Клиент для повторных запросов внутри теста. Создавший его код отвечает
        за вызов close после завершения работы.
    """

    logger_event_hook = HTTPLoggerEventHook(logger=logger)

    return Client(
        timeout=config.timeout,
        base_url=str(config.url),
        event_hooks={"request": [logger_event_hook.request]},
    )
