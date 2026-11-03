"""Сохраняет снимок состояния контейнеров Compose и результат его сбора."""

import json
import subprocess
from pathlib import Path

from .compose import compose_snapshot


def collect_diagnostics(compose_file: str, output_dir: Path) -> None:
    """Записывает состояние контейнеров и краткий результат запроса Compose.

    state.json содержит только Service, State, ExitCode и Health. Предыдущий
    снимок удаляется перед запросом. При сбое collection.txt содержит тип ошибки
    и код завершения либо timeout, без текста исключения, stdout или stderr.
    Текстовые логи контейнеров не запрашиваются.

    Args:
        compose_file: Файл Compose диагностируемого стенда.
        output_dir: Каталог для state.json и collection.txt; другие файлы
            в нём не изменяются.

    Raises:
        OSError: Если не удалось создать каталог или записать collection.txt.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        (output_dir / "state.json").unlink(missing_ok=True)
        snapshot = compose_snapshot(compose_file)
        (output_dir / "state.json").write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    except (OSError, subprocess.SubprocessError, ValueError) as error:
        collection = f"state: error_type={type(error).__name__}"
        if isinstance(error, subprocess.TimeoutExpired):
            collection += f" timeout={error.timeout}"
        elif isinstance(error, subprocess.CalledProcessError):
            collection += f" returncode={error.returncode}"
    else:
        collection = f"state: services={len(snapshot)}"
    (output_dir / "collection.txt").write_text(collection + "\n", encoding="utf-8")
