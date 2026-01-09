from functools import lru_cache

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from libs.config.postgres import PostgresConfig


@lru_cache(maxsize=True)
def get_postgres_session_factory(config: PostgresConfig) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        config.url,
        echo=False,
        future=True,
        pool_size=30,
        max_overflow=50,
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
