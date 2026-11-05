import logging
import os
import sys
from copy import copy
from functools import lru_cache


_LOG_FORMAT = "%(asctime)s.%(msecs)03d | %(levelname)s | %(name)s | %(message)s"
_TIME_FORMAT = "%H:%M:%S"
_LEVEL_COLORS = {
    logging.DEBUG: "\x1b[90m",
    logging.INFO: "\x1b[36m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[1;31m",
}


class _LevelColorFormatter(logging.Formatter):
    """Окрашивает уровень в консольной копии записи."""

    def format(self, record: logging.LogRecord) -> str:
        """Форматирует запись с цветом уровня для терминала.

        Args:
            record: Исходная запись, общая с другими обработчиками логов.

        Returns:
            Строка с ANSI-цветом для стандартного уровня логирования.
        """
        color = _LEVEL_COLORS.get(record.levelno)
        if color:
            record = copy(record)
            record.levelname = f"{color}{record.levelname}\x1b[0m"
        return super().format(record)


@lru_cache(maxsize=None)
def get_test_logger(name: str) -> logging.Logger:
    """Возвращает тестовый логгер с одним обработчиком на имя.

    Цвет используется в терминале, в обычном stderr PyCharm или при
    ISOLATION_LOG_COLOR=1. Непустая NO_COLOR отключает цвет в любом режиме,
    сохраняя метки и эмодзи.

    Args:
        name: Имя компонента, отображаемое в строках логов.

    Returns:
        Настроенный и закэшированный логгер компонента.
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    stream = console_handler.stream
    is_pycharm_console = stream is sys.__stderr__ and os.environ.get("PYCHARM_HOSTED") == "1"
    force_color = os.environ.get("ISOLATION_LOG_COLOR") == "1"
    use_color = not os.environ.get("NO_COLOR") and (
        stream.isatty() or is_pycharm_console or force_color
    )
    formatter_class = _LevelColorFormatter if use_color else logging.Formatter
    console_handler.setFormatter(formatter_class(_LOG_FORMAT, datefmt=_TIME_FORMAT))

    logger.addHandler(console_handler)

    return logger
