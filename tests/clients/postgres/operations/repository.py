"""Подготовка, чтение ID и точечное удаление тестовых операций в PostgreSQL."""

from collections.abc import Callable
from math import ceil, isfinite
from time import monotonic
from uuid import UUID

import allure
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session, sessionmaker

from tests.clients.postgres.operations.model import OperationsTestModel
from tests.clients.postgres.operations.session import operations_test_session_factory
from tests.clients.postgres.repository import PostgresTestRepository
from tests.tools.fakers import fake
from tests.tools.cleanup import CleanupManager
from tests.types.operations import OperationTestType, OperationTestStatus


class OperationsPostgresTestRepository(PostgresTestRepository[OperationsTestModel]):
    """Подготавливает, находит и удаляет тестовые операции в PostgreSQL.

    Создание фиксирует отдельную транзакцию; чтение ID фильтрует по полной
    тройке user/card/account, удаление использует только точный первичный ключ.
    При наличии cleanup_manager метод create регистрирует удаление после flush.
    Без менеджера за последующее удаление отвечает вызывающий код; решение
    о сохранении данных при ошибке принимает pytest-фикстура.

    Attributes:
        session_factory: Фабрика сессий SQLAlchemy, переданная базовому
            репозиторию при создании объекта.
    """

    def __init__(
        self,
        session_factory: sessionmaker[Session],
        cleanup_manager: CleanupManager | None = None,
    ) -> None:
        """Связывает repository с фабрикой сессий и реестром одного теста.

        Args:
            session_factory: Фабрика сессий базы Operations.
            cleanup_manager: Реестр удаления созданных строк. При None
                автоматическая регистрация отключена.
        """
        super().__init__(session_factory)
        self._cleanup_manager = cleanup_manager

    def create(
        self,
        instance: OperationsTestModel,
        *,
        on_created: Callable[[OperationsTestModel], None] | None = None,
    ) -> OperationsTestModel:
        """Вставляет операцию; при наличии manager регистрирует её удаление.

        Регистрация идёт после успешного flush, перед on_created, refresh и
        commit. Ошибка следующих этапов не теряет уже зарегистрированное
        удаление. Конфликтующий INSERT не регистрирует чужую существующую строку.

        Args:
            instance: Новая операция с заданным UUID.
            on_created: Дополнительный callback базового интерфейса create.
                Вызывается после регистрации при наличии manager, до refresh
                и commit.

        Returns:
            Модель после успешного commit и закрытия сессии.

        Raises:
            Exception: Ошибка вставки, регистрации, обновления модели или
                завершения транзакции. Очистка учтена только при наличии manager
                и успешной регистрации в нём.
        """
        def register_and_notify(created_instance: OperationsTestModel) -> None:
            """Регистрирует удаление при наличии manager, затем вызывает on_created."""
            if self._cleanup_manager is not None:
                self._cleanup_manager.add(
                    self.delete_by_id,
                    created_instance.id,
                    description=f"Operations row id={created_instance.id}",
                )
            if on_created is not None:
                on_created(created_instance)

        return super().create(instance, on_created=register_and_notify)

    @allure.step("Delete operation by id: {operation_id}")
    def delete_by_id(self, operation_id: UUID) -> None:
        """Удаляет только заданную строку и фиксирует отдельную транзакцию.

        Отсутствующая строка допустима: INSERT мог быть отменён после flush,
        либо запись уже удалена. Пользователь, карта и счёт не расширяют удаление.

        Args:
            operation_id: Точный первичный ключ принадлежащей тесту операции.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: Если выполнить или зафиксировать
                удаление не удалось. Ошибка передаётся вызывающему коду.
        """
        with self.session_write() as session:
            session.execute(delete(OperationsTestModel).where(OperationsTestModel.id == operation_id))

    def get_ids_by_owner(
        self, *, user_id: UUID, card_id: UUID, account_id: UUID, timeout: float | None = None
    ) -> set[UUID]:
        """Читает точные ID операций полной группы владельца.

        Args:
            user_id: Пользователь, заданный тестовым событием.
            card_id: Карта, заданная тестовым событием.
            account_id: Счёт, заданный тестовым событием.
            timeout: Оставшийся бюджет чтения в секундах. После получения
                соединения его остаток задаёт локальный statement_timeout.
                Ожидание пула и подключение имеют отдельные пределы engine;
                произвольный сетевой сбой не ограничен жёстким общим дедлайном.
                При None действует серверный предел, заданный фабрикой engine.

        Returns:
            Первичные ключи строк, одновременно совпавших по трём полям.

        Raises:
            ValueError: Если передан неположительный или неконечный бюджет.
            TimeoutError: Если бюджет исчерпан при получении соединения.
            sqlalchemy.exc.SQLAlchemyError: При ошибке подключения или запроса,
                включая серверную отмену по statement_timeout.
        """
        if timeout is not None and (not isfinite(timeout) or timeout <= 0):
            raise ValueError("Operations discovery timeout must be finite and positive")
        deadline = None if timeout is None else monotonic() + timeout
        with self.session_read() as session:
            if deadline is not None and session.get_bind().dialect.name == "postgresql":
                session.connection()
                remaining = deadline - monotonic()
                if remaining <= 0:
                    raise TimeoutError("Operations discovery budget exhausted during connection checkout")
                session.execute(
                    text("SELECT set_config('statement_timeout', :statement_timeout, true)"),
                    {"statement_timeout": f"{max(1, ceil(remaining * 1000))}ms"},
                )
            operation_ids = session.scalars(
                select(OperationsTestModel.id).where(
                    OperationsTestModel.user_id == user_id,
                    OperationsTestModel.card_id == card_id,
                    OperationsTestModel.account_id == account_id,
                )
            )
            return set(operation_ids)

    @allure.step("Create in progress purchase operation")
    def create_in_progress_purchase_operation(
        self,
        card_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> OperationsTestModel:
        """Создаёт и сохраняет покупку со статусом IN_PROGRESS.

        Неуказанные поля заполняются генератором тестовых данных.

        Args:
            card_id: Идентификатор карты. При None генерируется случайный UUID.
            user_id: Идентификатор пользователя. При None генерируется
                случайный UUID.

        Returns:
            Модель созданной операции после успешной фиксации транзакции.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: Если сохранить операцию в БД
                не удалось. Ошибка передаётся вызывающему коду.
        """
        return self.create(
            OperationsTestModel(
                id=fake.uuid(),
                type=OperationTestType.PURCHASE,
                status=OperationTestStatus.IN_PROGRESS,
                amount=fake.amount(),
                user_id=fake.uuid() if user_id is None else user_id,
                card_id=fake.uuid() if card_id is None else card_id,
                category=fake.category(),
                account_id=fake.uuid(),
                created_at=fake.date_time(),
            )
        )

    @allure.step("Create completed purchase operation")
    def create_completed_purchase_operation(
        self,
        user_id: UUID | None = None,
        account_id: UUID | None = None,
    ) -> OperationsTestModel:
        """Создаёт и сохраняет новую покупку со статусом COMPLETED.

        Неуказанные поля заполняются генератором тестовых данных.

        Args:
            user_id: Идентификатор пользователя. При None генерируется
                случайный UUID.
            account_id: Идентификатор счёта. При None генерируется случайный UUID.

        Returns:
            Модель созданной операции после успешной фиксации транзакции.

        Raises:
            sqlalchemy.exc.SQLAlchemyError: Если сохранить операцию в БД
                не удалось. Ошибка передаётся вызывающему коду.
        """
        return self.create(
            OperationsTestModel(
                id=fake.uuid(),
                type=OperationTestType.PURCHASE,
                status=OperationTestStatus.COMPLETED,
                amount=fake.amount(),
                user_id=fake.uuid() if user_id is None else user_id,
                card_id=fake.uuid(),
                category=fake.category(),
                account_id=fake.uuid() if account_id is None else account_id,
                created_at=fake.date_time(),
            )
        )


def get_operations_postgres_test_repository(
    cleanup_manager: CleanupManager | None = None,
) -> OperationsPostgresTestRepository:
    """Создаёт репозиторий с настроенной фабрикой сессий Operations.

    Возвращает новый репозиторий с общей operations_test_session_factory.
    Его методы создают и закрывают сессию на каждую операцию с БД.

    Args:
        cleanup_manager: Реестр одного теста для удаления вставленных операций.
            Без него автоматическая регистрация очистки не выполняется.

    Returns:
        Репозиторий, настроенный для подготовки данных в БД Operations.
    """
    return OperationsPostgresTestRepository(
        session_factory=operations_test_session_factory,
        cleanup_manager=cleanup_manager,
    )
