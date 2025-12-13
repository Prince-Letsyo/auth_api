import asyncio
from sqlalchemy.ext.asyncio.engine import AsyncEngine
from collections.abc import AsyncGenerator
from sqlalchemy.orm import DeclarativeBase
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from src.config import config
from src.utils.alembic_utils import upgrade_database


# Create async engine
engine: AsyncEngine = create_async_engine(url=config.database.session_url(), echo=False)

# Create async session factory
AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker[AsyncSession](
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get a new DB session per request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Optional: Create tables (run once during app startup)
async def init_db() -> None:
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, upgrade_database)
