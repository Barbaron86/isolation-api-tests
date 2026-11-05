"""Отложенная очистка ресурсов, принадлежащих одному тесту."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Any

from tests.tools.logger import get_test_logger


logger = get_test_logger("TEST_DATA_CLEANUP")


@dataclass(frozen=True)
class CleanupAction:
    """Хранит описание ресурса и подготовленный вызов его очистки.

    Attributes:
        description: Безопасное для отчёта описание с идентификатором ресурса.
        callback: Вызов без аргументов, выполняющий одно действие очистки.
    """

    description: str
    callback: Callable[[], object]


class CleanupManager:
    """Накапливает действия одного теста и выполняет их в обратном порядке.

    Менеджер не знает SQL и результатов pytest. Политику сохранения данных
    выбирает вызывающая фикстура. Обычные ошибки действий собираются в группу,
    чтобы одна ошибка не препятствовала оставшимся удалениям.
    """

    def __init__(self) -> None:
        """Создаёт пустой реестр, который нельзя разделять между тестами."""
        self._actions: list[CleanupAction] = []

    def add(
        self,
        callback: Callable[..., object],
        *args: Any,
        description: str,
        **kwargs: Any,
    ) -> None:
        """Запоминает вызов, не выполняя его при регистрации.

        Args:
            callback: Синхронный метод или функция; результат игнорируется.
                Coroutine callbacks не поддерживаются и не ожидаются.
            *args: Позиционные аргументы будущего вызова.
            description: Описание ресурса без паролей и содержимого записи.
            **kwargs: Именованные аргументы будущего вызова.
        """
        self._actions.append(CleanupAction(description, partial(callback, *args, **kwargs)))

    @property
    def pending_descriptions(self) -> tuple[str, ...]:
        """Возвращает описания ожидающих действий в порядке регистрации."""
        return tuple(action.description for action in self._actions)

    def cleanup(self) -> None:
        """Выполняет действия динамического стека LIFO до опустошения.

        Действия, добавленные callback во время очистки, выполняются раньше
        оставшихся старых действий. Обычные исключения не прерывают очистку.
        Повторный вызов пустого менеджера ничего не делает. Неуспешное действие
        также снимается с регистрации: автоматического повторного удаления нет.
        BaseException, включая KeyboardInterrupt и SystemExit, прерывает обход:
        ещё не начатые действия остаются в реестре. Аварийное завершение процесса
        не гарантирует очистку.

        Лог сообщает результат вызова действия по его описанию. Сбой логирования
        не влияет на выполнение остальных действий и собранные ошибки.

        Raises:
            ExceptionGroup: Если хотя бы одно действие завершилось ошибкой.
                Содержит исходные исключения с описаниями неуспешных действий.
        """
        errors: list[Exception] = []
        while self._actions:
            action = self._actions.pop()
            try:
                action.callback()
            except Exception as error:
                error.add_note(f"Cleanup action: {action.description}")
                errors.append(error)
                level, outcome = logging.ERROR, "failed"
            else:
                level, outcome = logging.INFO, "completed"
            try:
                logger.log(level, f"🧹 [CLEANUP] {action.description} · {outcome}")
            except Exception:
                # Очистка должна продолжаться при сбое обработчика логов.
                pass
        if errors:
            raise ExceptionGroup("Test resource cleanup failed", errors)
