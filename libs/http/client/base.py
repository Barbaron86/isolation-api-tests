from logging import Logger

from httpx import AsyncClient, Response, AsyncHTTPTransport, QueryParams, Headers

from libs.config.http import HTTPClientConfig
from libs.http.client.event_hooks.logger_event_hook import HTTPLoggerEventHook
from libs.http.client.transports.retry import RetryTransport


class HTTPClient:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def get(self, url: str, params: QueryParams | None = None) -> Response:
        return await self.client.get(url=url, params=params)


def build_http_client(logger: Logger, config: HTTPClientConfig, headers: Headers) -> AsyncClient:
    logger_event_hook = HTTPLoggerEventHook(logger=logger)
    retry_transport = RetryTransport(
        logger=logger,
        transport=AsyncHTTPTransport(),
        max_retries=config.retries
    )

    return AsyncClient(
        headers=headers,
        timeout=config.timeout,
        base_url=config.url,
        transport=retry_transport,
        event_hooks={
            'request': [logger_event_hook.request],
            'response': [logger_event_hook.response]
        }
    )
