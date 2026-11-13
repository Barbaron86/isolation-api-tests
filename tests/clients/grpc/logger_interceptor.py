from logging import Logger

from grpc import Call, RpcError, UnaryUnaryClientInterceptor


class GRPCLoggerInterceptor(UnaryUnaryClientInterceptor):
    """Логирует метод и итоговый статус unary-unary вызовов."""

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
        self.logger.info(f"→ {method}")

        def log_response(call: Call) -> None:
            self.logger.info(f"← {call.code().name} {method}")

        try:
            call = continuation(client_call_details, request)
        except RpcError as error:
            # Ошибка подготовки .future() может содержать статус gRPC.
            if isinstance(error, Call):
                log_response(error)
            raise

        call.add_done_callback(log_response)
        return call
