from unittest.mock import Mock, call, create_autospec
from uuid import UUID, uuid4

import pytest

from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.schema.operations import OperationEventTestSchema
from tests.tools import operations_cleanup
from tests.tools.cleanup import CleanupManager
from tests.tools.operations_cleanup import KafkaOperationsCleanup


class CleanupClock:
    """Двигает время по команде теста без настоящего ожидания."""

    def __init__(self) -> None:
        self.now = 0.0
        self.sleep = Mock(side_effect=self.advance)

    def monotonic(self) -> float:
        """Возвращает текущее время управляемых часов."""
        return self.now

    def advance(self, seconds: float) -> None:
        """Продвигает часы на указанное число секунд."""
        self.now += seconds


@pytest.fixture
def clock(monkeypatch: pytest.MonkeyPatch) -> CleanupClock:
    """Подменяет часы и паузу только в модуле сверки Kafka-операций."""
    clock = CleanupClock()
    monkeypatch.setattr(operations_cleanup, "monotonic", clock.monotonic)
    monkeypatch.setattr(operations_cleanup, "sleep", clock.sleep)
    return clock


@pytest.fixture
def repository() -> Mock:
    """Предоставляет репозиторий со строго заданным интерфейсом и без БД."""
    return create_autospec(OperationsPostgresTestRepository, instance=True, spec_set=True)


@pytest.fixture
def event() -> OperationEventTestSchema:
    """Готовит валидное событие с независимыми ID пользователя, карты и счёта."""
    return OperationEventTestSchema()


def owner(event: OperationEventTestSchema) -> dict[str, UUID]:
    """Возвращает параметры поиска строк, принадлежащих событию."""
    return {"user_id": event.user_id, "card_id": event.card_id, "account_id": event.account_id}


def test_waits_for_late_rows_and_deletes_each_new_id_once(
    repository: Mock, event: OperationEventTestSchema, clock: CleanupClock,
) -> None:
    """Снимает один исходный набор на владельца и ждёт оба новых ID."""
    baseline_id, first_id, second_id = uuid4(), uuid4(), uuid4()
    repository.get_ids_by_owner.side_effect = [
        {baseline_id},
        {baseline_id, first_id},
        {baseline_id, first_id},
        {baseline_id, first_id, second_id},
    ]
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=1.0, poll_interval=0.25)

    tracker.track(event)
    tracker.track(event)

    repository.get_ids_by_owner.assert_called_once_with(**owner(event), timeout=1.0)
    repository.delete_by_id.assert_not_called()

    manager.cleanup()

    assert repository.get_ids_by_owner.call_args_list == [
        call(**owner(event), timeout=1.0),
        call(**owner(event), timeout=1.0),
        call(**owner(event), timeout=0.75),
        call(**owner(event), timeout=0.5),
    ]
    assert repository.delete_by_id.call_args_list == [call(second_id), call(first_id)]
    assert clock.sleep.call_args_list == [call(0.25), call(0.25)]


@pytest.mark.parametrize("changed_id", ["user_id", "card_id", "account_id"])
def test_groups_events_by_all_three_owner_ids(
    repository: Mock, event: OperationEventTestSchema, clock: CleanupClock, changed_id: str,
) -> None:
    """Разделяет исходные наборы при изменении любого идентификатора владельца.

    Args:
        changed_id: Поле, которым отличается второе событие.
    """
    other_event = event.model_copy(update={changed_id: uuid4()})
    baseline_id, other_baseline_id, new_id, other_new_id = uuid4(), uuid4(), uuid4(), uuid4()
    repository.get_ids_by_owner.side_effect = [
        {baseline_id}, {other_baseline_id},
        {other_baseline_id, other_new_id}, {baseline_id, new_id},
    ]
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=1.0, poll_interval=0.25)

    tracker.track(event)
    tracker.track(other_event)
    manager.cleanup()

    assert repository.get_ids_by_owner.call_args_list == [
        call(**owner(event), timeout=1.0),
        call(**owner(other_event), timeout=1.0),
        call(**owner(other_event), timeout=1.0),
        call(**owner(event), timeout=1.0),
    ]
    assert repository.delete_by_id.call_args_list == [call(other_new_id), call(new_id)]
    clock.sleep.assert_not_called()


def test_deletes_discovered_rows_when_a_later_read_fails(
    repository: Mock, event: OperationEventTestSchema, clock: CleanupClock,
) -> None:
    """Удаляет уже найденный ID и передаёт исходную ошибку чтения."""
    first_id = uuid4()
    read_error = RuntimeError("database unavailable")
    repository.get_ids_by_owner.side_effect = [set(), {first_id}, read_error]
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=1.0, poll_interval=0.25)
    tracker.track(event)
    tracker.track(event)

    with pytest.raises(ExceptionGroup, match="Test resource cleanup failed") as error:
        manager.cleanup()

    assert error.value.exceptions == (read_error,)
    repository.delete_by_id.assert_called_once_with(first_id)
    clock.sleep.assert_called_once_with(0.25)


def test_stops_at_deadline_and_reports_partial_cleanup(
    repository: Mock, event: OperationEventTestSchema, clock: CleanupClock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Ограничивает последнюю паузу бюджетом и сообщает найденные строки."""
    first_id = uuid4()
    repository.get_ids_by_owner.side_effect = [set(), {first_id}, {first_id}]
    attach = Mock()
    monkeypatch.setattr(operations_cleanup.allure, "attach", attach)
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=0.75, poll_interval=0.5)
    tracker.track(event)
    tracker.track(event)

    manager.cleanup()

    assert clock.sleep.call_args_list == [call(0.5), call(0.25)]
    assert repository.get_ids_by_owner.call_args_list == [
        call(**owner(event), timeout=0.75),
        call(**owner(event), timeout=0.75),
        call(**owner(event), timeout=0.25),
    ]
    repository.delete_by_id.assert_called_once_with(first_id)
    attach.assert_called_once()
    details = attach.call_args.args[0]
    assert f"user={event.user_id} card={event.card_id} account={event.account_id}" in details
    assert "Events registered before publish: 2; rows found: 1" in details
    assert str(first_id) in details


def test_report_failures_preserve_deletion_after_a_slow_read(
    repository: Mock, event: OperationEventTestSchema, clock: CleanupClock, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Обрабатывает найденный ID после исчерпания бюджета внутри чтения."""
    first_id = uuid4()
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=1.0, poll_interval=0.25)
    repository.get_ids_by_owner.return_value = set()
    tracker.track(event)
    tracker.track(event)

    def read_past_deadline(**_query: object) -> set[UUID]:
        clock.advance(1.0)
        return {first_id}

    repository.get_ids_by_owner.side_effect = read_past_deadline
    warning = Mock(side_effect=RuntimeError("logger unavailable"))
    attach = Mock(side_effect=RuntimeError("Allure unavailable"))
    monkeypatch.setattr(operations_cleanup.logger, "warning", warning)
    monkeypatch.setattr(operations_cleanup.allure, "attach", attach)

    manager.cleanup()

    assert repository.get_ids_by_owner.call_count == 2
    repository.delete_by_id.assert_called_once_with(first_id)
    clock.sleep.assert_not_called()
    warning.assert_called_once()
    attach.assert_called_once()


def test_baseline_read_failure_leaves_no_cleanup_actions(
    repository: Mock, event: OperationEventTestSchema,
) -> None:
    """Передаёт ошибку исходного чтения до регистрации сверки."""
    read_error = RuntimeError("database unavailable")
    repository.get_ids_by_owner.side_effect = read_error
    manager = CleanupManager()
    tracker = KafkaOperationsCleanup(repository, manager, timeout=1.0, poll_interval=0.25)

    with pytest.raises(RuntimeError) as error:
        tracker.track(event)

    assert error.value is read_error
    assert manager.pending_descriptions == ()
    repository.delete_by_id.assert_not_called()


@pytest.mark.parametrize(
    "timeout,poll_interval",
    [
        pytest.param(0.0, 1.0, id="zero-timeout"),
        pytest.param(1.0, -1.0, id="negative-interval"),
        pytest.param(float("inf"), 1.0, id="infinite-timeout"),
        pytest.param(1.0, float("nan"), id="nan-interval"),
    ],
)
def test_rejects_invalid_time_budgets(repository: Mock, timeout: float, poll_interval: float) -> None:
    """Отклоняет неконечные и неположительные параметры ожидания.

    Args:
        timeout: Общий срок сверки строк.
        poll_interval: Пауза между чтениями.
    """
    with pytest.raises(ValueError, match="timeout and poll interval must be finite and positive"):
        KafkaOperationsCleanup(repository, CleanupManager(), timeout=timeout, poll_interval=poll_interval)
