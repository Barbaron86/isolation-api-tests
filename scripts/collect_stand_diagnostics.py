"""Собирает ограниченную диагностику Compose без окружения и payload событий."""

import argparse
from pathlib import Path

from stand.diagnostics import collect_diagnostics


def main() -> None:
    """Собирает отдельный артефакт диагностики перед остановкой стенда."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--compose-file", required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("stand-diagnostics"))
    args = parser.parse_args()
    collect_diagnostics(args.compose_file, args.output_dir)


if __name__ == "__main__":
    main()
