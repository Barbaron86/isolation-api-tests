"""Учёт строк Kafka-событий до публикации и ограниченная сверка при очистке."""

from dataclasses import dataclass
from math import isfinite
from time import monotonic, sleep
from uuid import UUID

import allure

from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.schema.operations import OperationEventTestSchema
from tests.tools.cleanup import CleanupManager
from tests.tools.logger import get_test_logger

logger = get_test_logger("KAFKA_OPERATIONS_CLEANUP")


@dataclass
class _PendingOperations:
    """Хранит состояние одной тестовой группы владельца.

    Attributes:
        baseline_ids: Первичные ключи, существовавшие до первой публикации.
        event_count: Число зарегистрированных попыток отправки;
            не подтверждает доставку Kafka или обработку приложением.
    """

    baseline_ids: set[UUID]
    event_count: int = 0


class KafkaOperationsCleanup:
    """Находит новые ID исключительно внутри группы владельца текущего теста.

    Тест выделяет собственные user/card/account UUID. Снимок до публикации
    дополнительно защищает уже существовавшие строки. Совместная публикация
    посторонним процессом с той же тройкой UUID не поддерживается.
    Решение о сохранении данных при ошибке принимает pytest-фикстура,
    а CleanupManager хранит и выполняет зарегистрированные действия.
    """

    def __init__(
            self,
            repository: OperationsPostgresTestRepository,
            cleanup_manager: CleanupManager,
            *,
            timeout: float,
            poll_interval: float,
    ) -> None:
        """Принимает зависимости одного теста и границы ожидания поздних строк.

        Args:
            repository: Чтение точных ID и их последующее удаление.
            cleanup_manager: Общий реестр действий текущего теста.
            timeout: Бюджет повторных чтений одной группы при teardown.
                Ожидание пула и подключение ограничены отдельно в engine;
                синхронный драйвер не гарантирует общий сетевой дедлайн.
            poll_interval: Интервал повторного чтения незавершённой группы.

        Raises:
            ValueError: Если границы ожидания не конечны или неположительны.
        """
        if any(not isfinite(value) or value <= 0 for value in (timeout, poll_interval)):
            raise ValueError("Kafka cleanup timeout and poll interval must be finite and positive")
        self._repository = repository
        self._cleanup_manager = cleanup_manager
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._pending: dict[tuple[UUID, UUID, UUID], _PendingOperations] = {}

    def track(self, event: OperationEventTestSchema) -> None:
        """Снимает исходные ID и регистрирует сверку до отправки события.

        Args:
            event: Подготовленное событие с принадлежащей тесту тройкой UUID.

        Raises:
            Exception: Ошибка чтения исходных ID; публикация ещё не начиналась.
        """
        user_id, card_id, account_id = event.user_id, event.card_id, event.account_id
        owner = (user_id, card_id, account_id)
        if owner not in self._pending:
            baseline_ids = self._repository.get_ids_by_owner(
                user_id=user_id, card_id=card_id, account_id=account_id, timeout=self._timeout
            )
            self._pending[owner] = _PendingOperations(set(baseline_ids))
            self._cleanup_manager.add(
                self._reconcile,
                owner,
                description=f"Kafka Operations owner user={user_id} card={card_id} account={account_id}",
            )
        self._pending[owner].event_count += 1

    def _reconcile(self, owner: tuple[UUID, UUID, UUID]) -> None:
        """Находит новые строки, регистрируя точные ID до следующего чтения.

        Args:
            owner: Полная группа владельца, зарегистрированная до публикации.

        Raises:
            Exception: Ошибка чтения БД. Уже найденные ID остаются в общем
                реестре и удаляются независимо от этой ошибки.
        """
        user_id, card_id, account_id = owner
        pending = self._pending[owner]
        deadline = monotonic() + self._timeout
        discovered_ids: set[UUID] = set()
        while True:
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            current_ids = self._repository.get_ids_by_owner(
                user_id=user_id,
                card_id=card_id,
                account_id=account_id,
                timeout=remaining
            )
            new_ids = current_ids - pending.baseline_ids - discovered_ids
            for operation_id in sorted(new_ids, key=str):
                self._cleanup_manager.add(
                    self._repository.delete_by_id,
                    operation_id,
                    description=f"Kafka Operations row id={operation_id}",
                )
            discovered_ids.update(new_ids)
            if len(discovered_ids) >= pending.event_count:
                return
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleep(min(self._poll_interval, remaining))
        self._report_unresolved(owner, pending.event_count, discovered_ids)

    @staticmethod
    def _report_unresolved(
            owner: tuple[UUID, UUID, UUID], expected_count: int, discovered_ids: set[UUID]
    ) -> None:
        """Сообщает границы очистки, сохраняя обязательные удаления при сбое отчёта.

        Args:
            owner: Безопасные идентификаторы для ручной проверки поздних записей.
            expected_count: Количество зарегистрированных попыток отправки;
                доставка этим счётчиком не подтверждается.
            discovered_ids: Уже зарегистрированные для удаления первичные ключи.
        """
        user_id, card_id, account_id = owner
        details = (
            f"Kafka cleanup deadline: user={user_id} card={card_id} account={account_id}\n"
            f"Events registered before publish: {expected_count}; rows found: {len(discovered_ids)}\n"
            f"Exact IDs registered for deletion: {', '.join(sorted(map(str, discovered_ids)))}\n"
            "Late writes after this deadline cannot be guaranteed cleaned up."
        )
        try:
            logger.warning(f"🧹 [CLEANUP] {details}")
        except Exception:
            pass
        try:
            allure.attach(
                details,
                name="Unresolved Kafka Operations cleanup",
                attachment_type=allure.attachment_type.TEXT,
            )
        except Exception:
            pass
