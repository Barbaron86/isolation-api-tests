"""Собирает состояние Compose и разрешённые технические сообщения сервисов."""

import json
import subprocess
from pathlib import Path

from .compose import compose_snapshot, run_compose
from .log_filter import filter_logs

LOG_SERVICES = ("kafka", "kafka-operations", "postgres", "postgres-init", "postgres-migrator-operations")


def _error_metadata(error: Exception) -> str:
    """Описывает сбой сбора без вывода команды и текста исключения.

    Args:
        error: Ошибка команды с таймаутом, разбора данных или записи файла.

    Returns:
        Класс ошибки и, при наличии, числовой код завершения либо таймаут.
    """
    metadata = f"error_type={type(error).__name__}"
    if isinstance(error, subprocess.TimeoutExpired):
        metadata += f" timeout={error.timeout}"
    elif isinstance(error, subprocess.CalledProcessError):
        metadata += f" returncode={error.returncode}"
    return metadata


def collect_diagnostics(compose_file: str, output_dir: Path) -> None:
    """Сохраняет очищенную диагностику, продолжая сбор после ошибки источника.

    Перед чтением источника удаляет его прошлый файл, чтобы ошибка нового сбора
    не оставила в артефакте сведения предыдущего запуска.

    Args:
        compose_file: Файл Compose диагностируемого стенда.
        output_dir: Отдельный каталог для состояния, логов и результатов сбора.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    collection = [
        "Allowlisted state/log metadata only; raw logs, environment and event payloads excluded."
    ]
    try:
        (output_dir / "state.json").unlink(missing_ok=True)
        snapshot = compose_snapshot(compose_file)
        (output_dir / "state.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
        collection.append(f"state: services={len(snapshot)}")
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        collection.append(f"state: {_error_metadata(error)}")
    for service in LOG_SERVICES:
        try:
            (output_dir / f"{service}.log").unlink(missing_ok=True)
            output = run_compose(
                compose_file, "logs", "--no-color", "--no-log-prefix", "--timestamps",
                "--tail", "200", "--since", "20m", service, timeout=20,
            )
            filtered = filter_logs(service, output)
            (output_dir / f"{service}.log").write_text(filtered, encoding="utf-8")
            collection.append(
                f"{service}: input_lines={len(output.splitlines())} saved_lines={len(filtered.splitlines())}"
            )
        except (OSError, subprocess.SubprocessError) as error:
            collection.append(f"{service}: {_error_metadata(error)}")
    (output_dir / "collection.txt").write_text("\n".join(collection) + "\n", encoding="utf-8")
