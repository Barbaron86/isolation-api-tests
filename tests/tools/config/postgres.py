from pydantic import BaseModel, Field, PostgresDsn


class PostgresClientTestConfig(BaseModel):
    """Задаёт подключение и отдельные пределы этапов работы PostgreSQL.

    Attributes:
        dsn: Адрес тестовой базы.
        echo: Логирование SQL через SQLAlchemy.
        connect_timeout: Предел подключения libpq в секундах для каждого хоста.
        pool_timeout: Предел ожидания свободного соединения в секундах.
        statement_timeout: Серверный предел одного SQL-запроса в секундах.
    """

    dsn: PostgresDsn
    echo: bool = True
    connect_timeout: int = Field(default=5, ge=2)
    pool_timeout: float = Field(default=5, gt=0, allow_inf_nan=False)
    statement_timeout: float = Field(default=5, gt=0, allow_inf_nan=False)
