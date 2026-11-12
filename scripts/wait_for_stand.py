"""Ожидает миграции, Kafka consumer и API до запуска интеграционных тестов."""

import argparse
import logging
import math

from stand.readiness import wait_for_stand


logger = logging.getLogger(__name__)


def main() -> None:
    """Проверяет параметры стенда и сообщает об успешной готовности.

    Raises:
        TimeoutError: Если стенд не стал готов в заданный срок.
        RuntimeError: Если обязательный сервис завершился с ошибкой.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-file", required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--http-ports", type=int, nargs=3, default=(8001, 8002, 8003))
    parser.add_argument("--grpc-ports", type=int, nargs=3, default=(9001, 9002, 9003))
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be finite and positive")
    if any(not 1 <= port <= 65535 for port in (*args.http_ports, *args.grpc_ports)):
        parser.error("ports must be between 1 and 65535")
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    wait_for_stand(args.compose_file, args.timeout, tuple(args.http_ports), tuple(args.grpc_ports))
    logger.info("Stand ready: migrations completed, Redis and Kafka healthy, HTTP/gRPC connected")


if __name__ == "__main__":
    main()
