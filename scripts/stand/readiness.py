"""Проверяет готовность стенда по состояниям Compose и подключениям к API."""

import subprocess
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

import grpc

from .compose import ServiceState, compose_snapshot


REQUIRED_SERVICES = {
    "kafka", "kafka-operations", "postgres", "postgres-init",
    "postgres-migrator-operations", "http-mock", "grpc-mock", "http-gateway",
    "grpc-gateway", "http-operations", "grpc-operations",
}
COMPLETED_SERVICES = {"postgres-init", "postgres-migrator-operations"}
HEALTHY_SERVICES = {"kafka", "postgres", "kafka-operations"}


def readiness_reason(snapshot: list[ServiceState]) -> str | None:
    """Находит причину неготовности после проверки завершившихся процессов.

    Args:
        snapshot: Разрешённые поля состояния сервисов Compose.

    Returns:
        Причина ожидания или None, если все обязательные сервисы готовы.

    Raises:
        RuntimeError: Если обязательный процесс завершился с ошибкой или неожиданно.
    """
    states = {record["Service"]: record for record in snapshot}
    for name in sorted(REQUIRED_SERVICES & states.keys()):
        state = states[name]
        if state["State"] in ("exited", "dead"):
            if name not in COMPLETED_SERVICES or state["ExitCode"] != 0:
                raise RuntimeError(f"Stand service failed: {name}, exit={state['ExitCode']}")

    for name in sorted(REQUIRED_SERVICES):
        if name not in states:
            return f"Missing required service: {name}"
        state = states[name]
        if name in COMPLETED_SERVICES:
            if state["State"] != "exited":
                return f"Waiting for {name} to complete: state={state['State']}"
        elif state["State"] != "running":
            return f"Waiting for {name} to run: state={state['State']}"
        elif name in HEALTHY_SERVICES and state["Health"] != "healthy":
            return f"Waiting for {name} health: health={state['Health'] or 'none'}"
    return None


def check_http(url: str, timeout: float) -> str | None:
    """Проверяет HTTP 200 от OpenAPI и закрывает ответ.

    Args:
        url: Адрес OpenAPI без вызова бизнес-операции.
        timeout: Таймаут HTTP-запроса в секундах.

    Returns:
        Причина отказа с адресом API или None при HTTP 200.
    """
    if timeout <= 0:
        return f"HTTP readiness deadline elapsed: {url}"
    try:
        with urlopen(url, timeout=timeout) as response:
            if response.status != 200:
                return f"HTTP readiness failed: {url}, status={response.status}"
    except HTTPError as error:
        error.close()
        return f"HTTP readiness failed: {url}, status={error.code}"
    except (OSError, URLError) as error:
        return f"HTTP readiness failed: {url}, error={type(error).__name__}"
    return None


def check_grpc(target: str, timeout: float) -> str | None:
    """Ожидает подключения gRPC и закрывает канал после проверки.

    Args:
        target: Хост и порт gRPC API.
        timeout: Срок ожидания подключения в секундах.

    Returns:
        Причина таймаута с адресом API или None при успешном подключении.
    """
    if timeout <= 0:
        return f"gRPC readiness deadline elapsed: {target}"
    with grpc.insecure_channel(target) as channel:
        try:
            grpc.channel_ready_future(channel).result(timeout=timeout)
        except grpc.FutureTimeoutError:
            return f"gRPC readiness timed out: {target}"
    return None


def apis_readiness_reason(
    timeout: float,
    http_ports: tuple[int, ...] = (8001, 8002, 8003),
    grpc_ports: tuple[int, ...] = (9001, 9002, 9003),
) -> str | None:
    """Проверяет API последовательно в пределах общего оставшегося срока.

    Args:
        timeout: Общий срок одного прохода в секундах.
        http_ports: Порты HTTP OpenAPI выбранного стенда.
        grpc_ports: Порты gRPC API выбранного стенда.

    Returns:
        Первая причина неготовности или None, если все API проверены вовремя.
    """
    deadline = time.monotonic() + timeout
    probes = [
        (check_http, f"http://localhost:{port}/openapi.json", "HTTP")
        for port in http_ports
    ]
    probes.extend((check_grpc, f"localhost:{port}", "gRPC") for port in grpc_ports)
    for check, endpoint, protocol in probes:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return f"{protocol} readiness deadline elapsed: {endpoint}"
        reason = check(endpoint, min(2, remaining))
        if reason is not None:
            return reason
        if time.monotonic() >= deadline:
            return f"{protocol} readiness deadline elapsed: {endpoint}"
    if time.monotonic() >= deadline:
        return "API readiness deadline elapsed"
    return None


def wait_for_stand(
    compose_file: str,
    timeout: float,
    http_ports: tuple[int, ...] = (8001, 8002, 8003),
    grpc_ports: tuple[int, ...] = (9001, 9002, 9003),
) -> None:
    """Ожидает готовность Compose и API без отправки бизнес-запросов.

    Args:
        compose_file: Файл Compose выбранного стенда.
        timeout: Общий срок ожидания в секундах.
        http_ports: Порты HTTP OpenAPI выбранного стенда.
        grpc_ports: Порты gRPC API выбранного стенда.

    Raises:
        TimeoutError: Если стенд не стал готов до истечения общего срока.
        RuntimeError: Если сервис упал или запрос Compose превысил свой таймаут.
    """
    deadline = time.monotonic() + timeout
    last_reason = "No Compose snapshot received before deadline"
    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        try:
            snapshot = compose_snapshot(compose_file, timeout=min(15, remaining))
        except subprocess.TimeoutExpired as error:
            if time.monotonic() < deadline:
                raise RuntimeError("Docker Compose state request timed out") from error
            last_reason = "Compose service snapshot timed out"
            break
        last_reason = readiness_reason(snapshot)
        remaining = deadline - time.monotonic()
        if last_reason is None and remaining > 0:
            last_reason = apis_readiness_reason(remaining, http_ports, grpc_ports)
            if last_reason is None and time.monotonic() < deadline:
                return
            if last_reason is None:
                last_reason = "API checks completed after readiness deadline"
        elif last_reason is None:
            last_reason = "Compose snapshot completed after readiness deadline"
        time.sleep(min(1, max(0, deadline - time.monotonic())))
    raise TimeoutError(f"Stand readiness timed out after {timeout:g}s: {last_reason}")
