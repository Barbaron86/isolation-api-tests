from logging import Logger
from time import perf_counter

from grpc import Call, RpcError, UnaryUnaryClientInterceptor


class GRPCLoggerInterceptor(UnaryUnaryClientInterceptor):
    """Логирует метод, статус и длительность unary-unary вызовов."""

    def __init__(self, logger: Logger):
        self.logger = logger

    def intercept_unary_unary(self, continuation, client_call_details, request):
        """Записывает итог после завершения вызова и возвращает исходный Call/Future.

        Args:
            continuation: Следующий шаг в цепочке перехватчиков gRPC.
            client_call_details: Параметры вызова, включая полный путь метода.
            request: Запрос, передаваемый следующему перехватчику или каналу.

        Returns:
            Объект вызова, который вернул continuation.
        """
        method = client_call_details.method
        self.logger.info(f"➡️ [REQUEST] gRPC {method}")
        started_at = perf_counter()

        def log_response(call: Call) -> None:
            duration_ms = int((perf_counter() - started_at) * 1000)
            self.logger.info(f"⬅️ [RESPONSE] gRPC {method} · {call.code().name} · {duration_ms} ms")

        try:
            call = continuation(client_call_details, request)
        except RpcError as error:
            # Ошибка подготовки .future() может содержать статус gRPC.
            if isinstance(error, Call):
                log_response(error)
            raise

        call.add_done_callback(log_response)
        return call
