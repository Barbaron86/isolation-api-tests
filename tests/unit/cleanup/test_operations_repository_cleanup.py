"""Проверяет регистрацию удаления и чтение ID операций для очистки."""

from datetime import datetime
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import Delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from tests.clients.postgres.operations import repository as operations_repository
from tests.clients.postgres.operations.model import OperationsTestModel
from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.tools.cleanup import CleanupManager
from tests.types.operations import OperationTestStatus, OperationTestType


@pytest.fixture
def operation_model() -> OperationsTestModel:
    """Создаёт операцию для проверки регистрации удаления.

    Returns:
        Несохранённая модель с независимыми ID строки и владельцев.
    """
    return OperationsTestModel(
        id=uuid4(),
        type=OperationTestType.PURCHASE,
        status=OperationTestStatus.COMPLETED,
        amount=123.45,
        user_id=uuid4(),
        card_id=uuid4(),
        account_id=uuid4(),
        category="cleanup-test",
        created_at=datetime(2026, 11, 1, 12, 0),
    )


@pytest.fixture
def postgres_session_with_checkout_delay(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Подменяет сессию PostgreSQL и имитирует получение соединения за 125 мс.

    Args:
        monkeypatch: Подменяет монотонные часы репозитория.

    Returns:
        Сессия, при вызове connection которой продвигаются тестовые часы.
    """
    elapsed = 0.0

    def checkout_connection() -> None:
        nonlocal elapsed
        elapsed += 0.125

    session = Mock(spec_set=Session)
    session.get_bind.return_value.dialect.name = "postgresql"
    session.connection.side_effect = checkout_connection
    session.scalars.return_value = []
    monkeypatch.setattr(operations_repository, "monotonic", lambda: elapsed)
    return session


def test_flush_conflict_does_not_schedule_deletion(operation_model: OperationsTestModel) -> None:
    """Проверяет, что конфликт первичного ключа оставляет чужой ID вне реестра.

    Args:
        operation_model: Модель с ID, который сессия считает уже занятым.
    """
    conflict = IntegrityError(None, None, ValueError("duplicate primary key"))
    insert_session = Mock(spec_set=Session)
    insert_session.flush.side_effect = conflict
    session_factory = Mock(return_value=insert_session)
    cleanup_manager = CleanupManager()
    repository = OperationsPostgresTestRepository(session_factory, cleanup_manager)

    with pytest.raises(IntegrityError) as failure:
        repository.create(operation_model)
    cleanup_manager.cleanup()

    assert failure.value is conflict
    insert_session.add.assert_called_once_with(operation_model)
    insert_session.rollback.assert_called_once_with()
    insert_session.commit.assert_not_called()
    insert_session.close.assert_called_once_with()
    insert_session.execute.assert_not_called()
    session_factory.assert_called_once_with()


def test_cleanup_registers_before_callback_and_deletes_by_primary_key(
    operation_model: OperationsTestModel,
) -> None:
    """Проверяет регистрацию до callback и точный фильтр SQL при удалении.

    Args:
        operation_model: Операция, удаление которой принадлежит текущему тесту.
    """
    insert_session = Mock(spec_set=Session)
    delete_session = Mock(spec_set=Session)
    session_factory = Mock(side_effect=[insert_session, delete_session])
    cleanup_manager = CleanupManager()
    repository = OperationsPostgresTestRepository(session_factory, cleanup_manager)

    def check_registration(created_model: OperationsTestModel) -> None:
        assert created_model is operation_model
        insert_session.flush.assert_called_once_with()
        insert_session.commit.assert_not_called()
        assert cleanup_manager.pending_descriptions == (f"Operations row id={operation_model.id}",)

    on_created = Mock(side_effect=check_registration)

    assert repository.create(operation_model, on_created=on_created) is operation_model
    cleanup_manager.cleanup()

    on_created.assert_called_once_with(operation_model)
    delete_session.execute.assert_called_once()
    (statement,) = delete_session.execute.call_args.args
    assert isinstance(statement, Delete)
    assert statement.table.compare(OperationsTestModel.__table__)
    assert statement.whereclause is not None
    assert statement.whereclause.compare(OperationsTestModel.id == operation_model.id)
    delete_session.commit.assert_called_once_with()


def test_commit_error_keeps_operation_scheduled_for_cleanup(
    operation_model: OperationsTestModel,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Проверяет очистку точного ID при потере подтверждения commit.

    Args:
        operation_model: Операция, вставка которой прошла flush.
        monkeypatch: Подменяет удаление операции наблюдаемым вызовом.
    """
    commit_error = RuntimeError("commit acknowledgement lost")
    insert_session = Mock(spec_set=Session)
    insert_session.commit.side_effect = commit_error
    cleanup_manager = CleanupManager()
    repository = OperationsPostgresTestRepository(Mock(return_value=insert_session), cleanup_manager)
    delete_by_id = Mock()
    monkeypatch.setattr(repository, "delete_by_id", delete_by_id)

    with pytest.raises(RuntimeError) as failure:
        repository.create(operation_model)
    cleanup_manager.cleanup()

    assert failure.value is commit_error
    insert_session.rollback.assert_called_once_with()
    insert_session.close.assert_called_once_with()
    delete_by_id.assert_called_once_with(operation_model.id)


def test_discovery_sets_statement_timeout_from_budget_remaining_after_checkout(
    operation_model: OperationsTestModel,
    postgres_session_with_checkout_delay: Mock,
) -> None:
    """Проверяет установку транзакционного таймаута до чтения ID операций.

    Args:
        operation_model: Источник идентификаторов владельца и найденной строки.
        postgres_session_with_checkout_delay: Сессия, расходующая 125 мс бюджета.
    """
    session = postgres_session_with_checkout_delay
    session.scalars.return_value = [operation_model.id]
    repository = OperationsPostgresTestRepository(Mock(return_value=session))

    operation_ids = repository.get_ids_by_owner(
        user_id=operation_model.user_id,
        card_id=operation_model.card_id,
        account_id=operation_model.account_id,
        timeout=0.25,
    )

    assert operation_ids == {operation_model.id}
    session.connection.assert_called_once_with()
    session.execute.assert_called_once()
    statement, parameters = session.execute.call_args.args
    assert str(statement) == "SELECT set_config('statement_timeout', :statement_timeout, true)"
    assert parameters == {"statement_timeout": "125ms"}
    session.scalars.assert_called_once()
    session_methods = [method_call[0] for method_call in session.method_calls]
    assert session_methods.index("execute") < session_methods.index("scalars")
    session.close.assert_called_once_with()


def test_discovery_skips_sql_if_checkout_exhausts_budget(
    operation_model: OperationsTestModel,
    postgres_session_with_checkout_delay: Mock,
) -> None:
    """Проверяет отказ от SQL и закрытие сессии ровно на границе дедлайна.

    Args:
        operation_model: Источник идентификаторов владельца.
        postgres_session_with_checkout_delay: Сессия, расходующая весь бюджет.
    """
    session = postgres_session_with_checkout_delay
    repository = OperationsPostgresTestRepository(Mock(return_value=session))

    with pytest.raises(TimeoutError, match="budget exhausted"):
        repository.get_ids_by_owner(
            user_id=operation_model.user_id,
            card_id=operation_model.card_id,
            account_id=operation_model.account_id,
            timeout=0.125,
        )

    session.connection.assert_called_once_with()
    session.execute.assert_not_called()
    session.scalars.assert_not_called()
    session.close.assert_called_once_with()
