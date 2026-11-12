from logging import Logger

from httpx import Request, Response


def _request_path(request: Request) -> str:
    """Берёт путь для лога, сохраняя URL-кодирование.

    Args:
        request: Подготовленный HTTPX-запрос.

    Returns:
        Путь без query-параметров.
    """
    return request.url.raw_path.partition(b"?")[0].decode("ascii")


class HTTPLoggerEventHook:
    """Записывает запрос и статус ответа средствами HTTPX event hooks."""

    def __init__(self, logger: Logger) -> None:
        """Сохраняет логгер компонента.

        Args:
            logger: Логгер, используемый тестовым клиентом сервиса.
        """
        self.logger = logger

    def request(self, request: Request) -> None:
        """Логирует метод и путь HTTP-запроса перед отправкой.

        Args:
            request: Подготовленный HTTPX-запрос. В лог попадают метод и путь.
        """
        self.logger.info(f"→ {request.method} {_request_path(request)}")

    def response(self, response: Response) -> None:
        """Логирует статус ответа, метод и путь исходного запроса.

        Args:
            response: Ответ HTTPX на этапе получения заголовков, до чтения тела.
        """
        request = response.request
        status = f"{response.status_code} {response.reason_phrase}".rstrip()
        self.logger.info(f"← {status} {request.method} {_request_path(request)}")
