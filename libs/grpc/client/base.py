from logging import Logger

import grpc
import grpc.experimental.gevent as grpc_gevent

from libs.config.grpc import GRPCClientConfig
from libs.grpc.client.interceptors.logger_interceptor import GRPCLoggerInterceptor
from libs.grpc.client.interceptors.retries_interceptor import GRPCRetriesInterceptor, DEFAULT_GRPC_RETRY_CODES
from libs.grpc.client.interceptors.timeout_interceptor import GRPCTimeoutInterceptor

grpc_gevent.init_gevent()


class GRPCClient:
    def __init__(self, channel: grpc.Channel):
        self.channel = channel


def build_grpc_channel(
        logger: Logger,
        config: GRPCClientConfig,
        retry_codes: tuple[grpc.StatusCode, ...] = DEFAULT_GRPC_RETRY_CODES
) -> grpc.Channel:
    interceptors = [
        GRPCLoggerInterceptor(logger=logger),
        GRPCTimeoutInterceptor(timeout=config.timeout),
        GRPCRetriesInterceptor(logger=logger, max_retries=config.retries, retry_codes=retry_codes)
    ]

    return grpc.aio.insecure_channel(config.url, interceptors=interceptors)
