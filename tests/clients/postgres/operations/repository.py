"""Подготовка операций в PostgreSQL для тестов чтения и фильтрации API."""

from collections.abc import Callable
from uuid import UUID

import allure
from sqlalchemy import delete
from sqlalchemy.orm import Session, sessionmaker

from tests.clients.postgres.operations.model import OperationsTestModel
from tests.clients.postgres.operations.session import operations_test_session_factory
from tests.clients.postgres.repository import PostgresTestRepository
from tests.tools.fakers import fake
from tests.tools.cleanup import CleanupManager
from tests.types.operations import OperationTestType, OperationTestStatus


class OperationsPostgresTestRepository(PostgresTestRepository[OperationsTestModel]):
    """Создаёт тестовые записи в таблице operations.

    Методы формируют ORM-модель покупки и передают её базовому методу create.
    Каждый успешный вызов сохраняет одну запись и фиксирует транзакцию до
    возврата модели. Сессия записи закрывается базовым репозиторием.

    Подготовка напрямую в БД позволяет проверять чтение и фильтрацию API
    независимо от обработки Kafka-событий. С переданным cleanup_manager
    регистрирует удаление каждой вставленной строки по точному ID. Политику
    очистки или сохранения для отладки выбирает фикстура pytest.
    Без менеджера последующим удалением управляет вызывающий код.

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
        """Сохраняет операцию и регистрирует удаление после успешного INSERT.

        Args:
            instance: Новая операция с заданным UUID.
            on_created: Дополнительный callback базового интерфейса create.
                Вызывается после автоматической регистрации очистки, до commit.

        Returns:
            Модель после успешного commit и закрытия сессии.

        Raises:
            Exception: Ошибка вставки, регистрации, обновления модели или
                завершения транзакции. Вставленная строка уже учтена менеджером
                при ошибке после flush; конфликтующий INSERT не регистрируется.
        """
        def register_and_notify(created_instance: OperationsTestModel) -> None:
            """Регистрирует удаление перед вызовом пользовательского callback.

            Args:
                created_instance: Операция после успешного INSERT.
            """
            self._register_cleanup(created_instance)
            if on_created is not None:
                on_created(created_instance)

        return super().create(instance, on_created=register_and_notify)

    def _register_cleanup(self, instance: OperationsTestModel) -> None:
        """Запоминает удаление вставленной строки до завершения транзакции.

        Args:
            instance: Операция, для которой успешно выполнен flush.
        """
        if self._cleanup_manager is not None:
            self._cleanup_manager.add(
                self.delete_by_id,
                instance.id,
                description=f"Operations row id={instance.id}",
            )

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

    @allure.step("Create in progress purchase operation")
    def create_in_progress_purchase_operation(
        self,
        card_id: UUID | None = None,
        user_id: UUID | None = None,
    ) -> OperationsTestModel:
        """Создаёт и сохраняет покупку со статусом IN_PROGRESS.

        Переданные идентификаторы позволяют подготовить несколько операций
        одного пользователя или одной карты. Остальные поля заполняются
        генератором тестовых данных. Тип операции всегда PURCHASE.

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

        Переданные идентификаторы позволяют подготовить несколько операций
        одного пользователя или одного счёта. Остальные поля заполняются
        генератором тестовых данных. Тип операции всегда PURCHASE.

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

    Каждый вызов возвращает новый объект репозитория, использующий общую
    operations_test_session_factory. Созданием и закрытием сессий управляют
    методы базового репозитория при выполнении операций с БД.

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
