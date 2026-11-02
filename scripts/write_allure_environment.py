"""Формирование Allure Environment в среде запуска тестов CI."""

import os
import platform
import subprocess
from importlib.metadata import version
from pathlib import Path


def collect_environment() -> dict[str, str]:
    """Собирает версии среды, настройки запуска и SHA текущего checkout.

    Читает только TEST_MARKER и TEST_COMPOSE_FILE, заданные в job запуска тестов.

    Returns:
        Именованные параметры для блока Environment в Allure.

    Raises:
        KeyError: Если обязательные настройки CI не заданы.
    """
    return {
        "Environment": "CI / Docker Compose",
        "Runner.OS": platform.platform(),
        "Runner.Python": platform.python_version(),
        "pytest": version("pytest"),
        "allure-pytest": version("allure-pytest"),
        "Test.Selection": os.environ["TEST_MARKER"],
        "Stand.Compose": os.environ["TEST_COMPOSE_FILE"],
        "Git.Revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True,
        ).strip(),
    }


def write_environment(environment: dict[str, str], results_dir: Path) -> None:
    """Сохраняет параметры в environment.properties каталога результатов.

    Создаёт каталог при необходимости. Остальные файлы Allure сохраняются.

    Args:
        environment: Параметры текущего запуска для отображения в отчёте.
        results_dir: Каталог результатов, передаваемый pytest и генератору Allure.
    """
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "environment.properties").write_text(
        "\n".join(f"{name}={value}" for name, value in environment.items()) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    """Записывает метаданные CI в allure-results; запускается из корня проекта."""
    write_environment(collect_environment(), Path("allure-results"))


if __name__ == "__main__":
    main()
