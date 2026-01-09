import asyncio
from logging import Logger
from typing import Callable

import grpc
from grpc.aio import UnaryUnaryClientInterceptor, ClientCallDetails
from grpc.aio._call import UnaryUnaryCall
from grpc.aio._typing import RequestType, ResponseType

DEFAULT_GRPC_RETRY_CODES: tuple[grpc.StatusCode, ...] = (
    grpc.StatusCode.UNAVAILABLE,
    grpc.StatusCode.DEADLINE_EXCEEDED,
)


class GRPCRetriesInterceptor(UnaryUnaryClientInterceptor):
    def __init__(
            self,
            logger: Logger,
            max_retries: int = 5,
            retry_delay: float = 0.5,
            retry_codes: tuple[grpc.StatusCode, ...] = DEFAULT_GRPC_RETRY_CODES
    ):
        self.logger = logger
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_codes = retry_codes

    async def intercept_unary_unary(
            self,
            continuation: Callable[[ClientCallDetails, RequestType], UnaryUnaryCall],
            client_call_details: ClientCallDetails,
            request: RequestType,
    ) -> UnaryUnaryCall | ResponseType:
        response: UnaryUnaryCall | None = None
        for _ in range(self.max_retries):
            response = await continuation(client_call_details, request)
            code = await response.code()
            if code not in self.retry_codes:
                return response

            self.logger.error(
                f'Unexpected response code: "{code}" for {client_call_details.method}, retrying'
            )

            await asyncio.sleep(self.retry_delay)

        return response
