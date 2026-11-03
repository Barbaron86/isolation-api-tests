from math import ceil

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker, Session

from tests.tools.config.postgres import PostgresClientTestConfig


def get_postgres_test_session_factory(config: PostgresClientTestConfig) -> sessionmaker[Session]:
    """Создаёт фабрику с ограничениями пула, подключения и SQL-запроса.

    Пределы относятся к отдельным этапам, а не к общей длительности вызова.
    Синхронный драйвер не гарантирует жёсткий сетевой дедлайн; например,
    statement_timeout действует на сервере и не прерывает потерю ответа в сети.

    Args:
        config: DSN, логирование и отдельные пределы PostgreSQL.

    Returns:
        Фабрика с общим для её потребителей engine. Repository создаёт отдельную
        Session на вызов, управляет транзакцией и закрывает её. Отключённый autoflush
        оставляет момент INSERT явным; expire_on_commit=False позволяет читать
        подготовленную ORM-модель после commit. Готовую Session между потоками
        или процессами не разделяют.
    """
    connection_options = " ".join(make_url(str(config.dsn)).normalized_query.get("options", ()))
    statement_timeout_ms = max(1, ceil(config.statement_timeout * 1000))
    connection_options = f"{connection_options} -c statement_timeout={statement_timeout_ms}".strip()

    engine = create_engine(
        url=str(config.dsn),
        echo=config.echo,
        future=True,
        pool_pre_ping=True,
        pool_timeout=config.pool_timeout,
        connect_args={
            "connect_timeout": config.connect_timeout,
            "options": connection_options,
        },
    )

    return sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
