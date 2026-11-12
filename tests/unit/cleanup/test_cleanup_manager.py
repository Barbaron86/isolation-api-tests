"""Юнит-тесты регистрации, выполнения и диагностики очистки."""

from unittest.mock import Mock, call

import pytest

from tests.tools import cleanup
from tests.tools.cleanup import CleanupManager


def test_cleanup_preserves_arguments_and_runs_in_reverse_registration_order() -> None:
    """Откладывает callbacks и передаёт исходные аргументы в порядке LIFO."""
    manager = CleanupManager()
    delete_record = Mock()
    manager.add(delete_record, "parent", owner_id="user-17", description="parent record")
    manager.add(delete_record, "child", owner_id="user-42", description="child record")

    delete_record.assert_not_called()
    manager.cleanup()

    assert delete_record.call_args_list == [call("child", owner_id="user-42"), call("parent", owner_id="user-17")]


def test_cleanup_runs_actions_registered_during_cleanup_before_older_actions() -> None:
    """Сразу удаляет ресурс, найденный одним из действий очистки."""
    manager = CleanupManager()
    attempted = []

    def discover_record() -> None:
        attempted.append("discover")
        manager.add(attempted.append, "discovered", description="discovered record")

    manager.add(attempted.append, "existing", description="existing record")
    manager.add(discover_record, description="discover records")

    manager.cleanup()

    assert attempted == ["discover", "discovered", "existing"]
    assert manager.pending_descriptions == ()


def test_cleanup_attempts_all_actions_and_aggregates_original_errors_without_retrying() -> None:
    """Собирает исходные ошибки и сохраняет попытку очистки остальных ресурсов."""
    manager = CleanupManager()
    attempted = []
    parent_error = ValueError("parent deletion failed")
    child_error = RuntimeError("child deletion failed")

    def fail_cleanup(record: str, error: Exception) -> None:
        attempted.append(record)
        raise error

    manager.add(fail_cleanup, "parent", parent_error, description="parent record")
    manager.add(attempted.append, "independent", description="independent record")
    manager.add(fail_cleanup, "child", child_error, description="child record")

    with pytest.raises(ExceptionGroup) as failure:
        manager.cleanup()
    manager.cleanup()

    assert attempted == ["child", "independent", "parent"]
    assert failure.value.exceptions == (child_error, parent_error)
    assert child_error.__notes__ == ["Cleanup action: child record"]
    assert parent_error.__notes__ == ["Cleanup action: parent record"]
    assert manager.pending_descriptions == ()


def test_logging_error_does_not_replace_cleanup_error_or_prevent_remaining_actions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Сохраняет ошибку удаления и продолжает очистку при отказе логирования.

    Args:
        monkeypatch: Фикстура для имитации отказа логгера.
    """
    manager = CleanupManager()
    delete_error = RuntimeError("delete failed")
    remaining_delete = Mock()
    monkeypatch.setattr(cleanup.logger, "log", Mock(side_effect=OSError("log failed")))
    manager.add(remaining_delete, description="remaining record")
    manager.add(Mock(side_effect=delete_error), description="failed record")

    with pytest.raises(ExceptionGroup) as failure:
        manager.cleanup()

    assert failure.value.exceptions == (delete_error,)
    remaining_delete.assert_called_once_with()
    assert manager.pending_descriptions == ()


def test_cleanup_interruption_leaves_unstarted_actions_pending() -> None:
    """Оставляет незапущенные действия в реестре при остановке выполнения."""
    manager = CleanupManager()
    remaining_delete = Mock()
    interrupt = SystemExit(2)
    interrupted_delete = Mock(side_effect=interrupt)
    manager.add(remaining_delete, description="remaining record")
    manager.add(interrupted_delete, description="interrupted record")

    with pytest.raises(SystemExit) as failure:
        manager.cleanup()

    assert failure.value is interrupt
    remaining_delete.assert_not_called()
    assert manager.pending_descriptions == ("remaining record",)

    manager.cleanup()

    interrupted_delete.assert_called_once_with()
    remaining_delete.assert_called_once_with()


def test_cleanup_executes_callback() -> None:
    """Выполняет сохранённый callback в момент очистки."""
    manager = CleanupManager()
    completed_actions = []

    def delete_operation() -> None:
        completed_actions.append(1)

    manager.add(delete_operation, description="Delete operation")

    assert completed_actions == []

    manager.cleanup()

    assert completed_actions == [1]


def test_cleanup_pending_descriptions() -> None:
    """Проверяет описания ожидающих действий до очистки и после неё."""
    manager = CleanupManager()

    manager.add(lambda: None, description="Delete user")
    manager.add(lambda: None, description="Delete operation")

    assert len(manager.pending_descriptions) == 2
    assert manager.pending_descriptions == ("Delete user", "Delete operation")

    manager.cleanup()

    assert len(manager.pending_descriptions) == 0
    assert manager.pending_descriptions == ()
