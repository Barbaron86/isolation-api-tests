"""Ограниченные по времени команды Docker Compose и снимок контейнеров."""

import json
import subprocess
from typing import TypedDict


class ServiceState(TypedDict):
    """Поля Docker, используемые проверкой готовности и отчётом.

    Attributes:
        Service: Имя сервиса из Compose.
        State: Состояние процесса контейнера.
        ExitCode: Код завершения, если процесс уже остановился.
        Health: Результат healthcheck либо пустое значение.
    """

    Service: str
    State: str
    ExitCode: int | None
    Health: str | None


def run_compose(compose_file: str, *arguments: str, timeout: float) -> str:
    """Выполняет Compose без shell и возвращает stdout успешной команды.

    Args:
        compose_file: Файл выбранного стенда.
        *arguments: Аргументы команды после выбора файла.
        timeout: Предельное время команды в секундах.

    Returns:
        Текст stdout. Ошибки запуска и выполнения передаются вызывающему коду.
    """
    result = subprocess.run(
        ["docker", "compose", "-f", compose_file, *arguments],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        check=True,
    )
    return result.stdout


def compose_snapshot(compose_file: str, timeout: float = 15) -> list[ServiceState]:
    """Читает состояние всех контейнеров, исключая команды и конфигурацию.

    Args:
        compose_file: Файл выбранного стенда.
        timeout: Предельное время запроса Docker.

    Returns:
        Четыре поля каждого контейнера из JSON-массива или JSON Lines Compose.
    """
    output = run_compose(compose_file, "ps", "--all", "--format", "json", timeout=timeout).strip()
    records = json.loads(output) if output.startswith("[") else [json.loads(line) for line in output.splitlines()]
    for record in records:
        if not isinstance(record, dict) or not all(isinstance(record.get(key), str) for key in ("Service", "State")):
            raise ValueError("Invalid Docker Compose state record")
    return [
        ServiceState(
            Service=record["Service"],
            State=record["State"],
            ExitCode=record.get("ExitCode"),
            Health=record.get("Health"),
        )
        for record in records
    ]
