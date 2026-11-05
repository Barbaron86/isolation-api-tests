from logging import Logger

from httpx import Request


class HTTPLoggerEventHook:
    """Записывает метод и путь подготовленного HTTP-запроса перед отправкой."""

    def __init__(self, logger: Logger) -> None:
        """Сохраняет логгер компонента.

        Args:
            logger: Логгер, используемый тестовым клиентом сервиса.
        """
        self.logger = logger

    def request(self, request: Request) -> None:
        """Логирует HTTP-запрос на этапе отправки.

        Args:
            request: Подготовленный HTTPX-запрос. В лог попадают метод и путь.
        """
        path = request.url.raw_path.partition(b"?")[0].decode("ascii")
        self.logger.info(f"➡️ [REQUEST] HTTP {request.method} {path}")
