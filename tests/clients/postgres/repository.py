"""Сессии и транзакции для прямой подготовки тестовых данных."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from typing import Generic, TypeVar

from sqlalchemy.orm import Session, sessionmaker

from tests.clients.postgres.base import BaseTestModel


ModelT = TypeVar("ModelT", bound=BaseTestModel)


class PostgresTestRepository(Generic[ModelT]):
    """Выполняет операции ORM через короткоживущие сессии.

    Каждая запись фиксируется отдельно. Закрытие сессии и последующий rollback
    другой транзакции не удаляют уже сохранённые строки.

    Attributes:
        session_factory: Настроенная фабрика сессий SQLAlchemy.
    """

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        """Принимает фабрику без создания собственного engine.

        Args:
            session_factory: Фабрика сессий нужной тестовой базы.
        """
        self.session_factory = session_factory

    @contextmanager
    def session_read(self) -> Generator[Session, None, None]:
        """Предоставляет сессию чтения и закрывает её при выходе.

        Yields:
            Сессия SQLAlchemy без автоматического commit.
        """
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    @contextmanager
    def session_write(self) -> Generator[Session, None, None]:
        """Фиксирует успешную запись или откатывает текущую транзакцию.

        Уже завершённые транзакции предыдущих вызовов не затрагиваются.

        Yields:
            Сессия, которая будет закрыта после commit или rollback.

        Raises:
            Exception: Передаёт ошибку операции или commit после попытки
                rollback. SQLAlchemy также может сообщить ошибку закрытия.
        """
        session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create(
        self,
        instance: ModelT,
        *,
        on_created: Callable[[ModelT], None] | None = None,
    ) -> ModelT:
        """Вставляет модель, обновляет её поля и фиксирует транзакцию.

        Callback вызывается после успешного flush, до refresh и commit.
        К этому моменту INSERT принят БД, но ещё может быть отменён. Регистрация
        удаления здесь учитывает ошибки последующих этапов, включая commit.
        При конфликте INSERT с существующим ID callback не вызывается.

        Args:
            instance: Новая ORM-модель для вставки.
            on_created: Необязательное действие после успешного INSERT.
                Получает модель внутри ещё открытой транзакции.

        Returns:
            Модель после refresh и успешного завершения сессии записи.

        Raises:
            Exception: Ошибка INSERT, callback, refresh, commit или закрытия
                сессии. Для открытой транзакции предпринимается rollback.
        """
        with self.session_write() as session:
            session.add(instance)
            session.flush()
            if on_created is not None:
                on_created(instance)
            session.refresh(instance)
        return instance
