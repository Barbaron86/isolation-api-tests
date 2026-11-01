"""Подготовка операций в PostgreSQL для тестов чтения и фильтрации API."""

import allure

from tests.clients.postgres.operations.model import OperationsTestModel
from tests.clients.postgres.operations.session import operations_test_session_factory
from tests.clients.postgres.repository import PostgresTestRepository
from tests.tools.fakers import fake
from tests.types.operations import OperationTestType, OperationTestStatus
from uuid import UUID


class OperationsPostgresTestRepository(PostgresTestRepository):
    """Создаёт тестовые записи в таблице operations.

    Методы формируют ORM-модель покупки и передают её базовому методу create.
    Каждый успешный вызов сохраняет одну запись и фиксирует транзакцию до
    возврата модели. Сессия записи закрывается базовым репозиторием.

    Подготовка напрямую в БД позволяет проверять чтение и фильтрацию API
    независимо от обработки Kafka-событий. Созданные строки остаются в БД;
    за их последующее удаление отвечает вызывающий код или фикстура.

    Attributes:
        session_factory: Фабрика сессий SQLAlchemy, переданная базовому
            репозиторию при создании объекта.
    """

    @allure.step("Create in progress purchase operation")
    def create_in_progress_purchase_operation(self, card_id: UUID | None = None,
                                              user_id: UUID | None = None) -> OperationsTestModel:
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
    def create_completed_purchase_operation(self, user_id: UUID | None = None,
                                            account_id: UUID | None = None) -> OperationsTestModel:
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


def get_operations_postgres_test_repository() -> OperationsPostgresTestRepository:
    """Создаёт репозиторий с настроенной фабрикой сессий Operations.

    Каждый вызов возвращает новый объект репозитория, использующий общую
    operations_test_session_factory. Созданием и закрытием сессий управляют
    методы базового репозитория при выполнении операций с БД.

    Returns:
        Репозиторий, настроенный для подготовки данных в БД Operations.
    """
    return OperationsPostgresTestRepository(
        session_factory=operations_test_session_factory
    )
