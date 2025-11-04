import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

load_dotenv()

DEFAULT_SQLITE_URL = "sqlite+aiosqlite:///submissions.db"


def _normalize_database_url(url: str) -> str:
    """Ensure the URL uses SQLAlchemy's async dialect names."""

    if url.startswith("postgres://"):
        # Render provides DATABASE_URL=postgres://...; asyncpg expects postgresql+asyncpg://
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    if url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
        url = url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    return url


# Set DATABASE_URL for local dev (`sqlite+aiosqlite:///submissions.db`) or production.
# To point at Render's Postgres instance run:
#   export DATABASE_URL=postgres://username:password@host:port/dbname
# The helper above automatically upgrades it to postgresql+asyncpg:// and `init_db()`
# will create the tables in the new database on startup, so switching from SQLite to
# Postgres is just a restart away (migrate existing rows separately if needed).
DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", DEFAULT_SQLITE_URL))

engine = create_async_engine(DATABASE_URL, future=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def init_db() -> None:
    """Create tables if they do not yet exist."""

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async SQLAlchemy session for FastAPI dependencies."""

    async with AsyncSessionLocal() as session:
        yield session
