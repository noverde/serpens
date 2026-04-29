"""SQLAlchemy 2.0 helpers — opinionated engine setup, session factory, model base.

Thin layer over SA 2.0. Apps use SA directly for queries (`select`, `insert`, etc.):

    from sqlalchemy import select
    from serpens.database import SessionLocal, Base, TimestampMixin

    class User(TimestampMixin, Base):
        ...

    with SessionLocal() as sess:
        sess.scalars(select(User)).all()
        sess.commit()

For Lambda / scripts where you want commit-on-exit / rollback-on-exception managed
for you, use `db_session()` instead of `SessionLocal()`:

    with db_session() as sess:
        sess.add(User(name="Ana"))
    # commits on exit; rolls back on exception

What this module owns and why:

- Engine config that is pegadinha in production (Cloud SQL keepalives, Postgres
  `statement_timeout` / `lock_timeout` / `idle_in_transaction_session_timeout`,
  `pool_use_lifo`, `pool_pre_ping`, scheme normalization). Centralized so a fix
  is one PR, not 24.
- Lambda-aware defaults (set `DB_POOL_SIZE=1` / `DB_MAX_OVERFLOW=0` in your
  Lambda env to avoid pool churn).
- Symmetric async API.
- Alembic helper (`serpens.database.alembic.run_migrations`) for migrations.

What this module does NOT own:

- Query construction (use `sqlalchemy` directly).
- Session-as-global / `current_session()` / `EntityMixin` (Pony pattern).
"""

import asyncio
import os
from contextlib import asynccontextmanager, contextmanager
from datetime import datetime
from typing import AsyncIterator, Iterator, Optional

from sqlalchemy import DateTime, Engine, MetaData, create_engine, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    mapped_column,
    sessionmaker,
)

from serpens import envvars

__all__ = [
    "Base",
    "TimestampMixin",
    "declarative_base",
    "bind",
    "dispose",
    "SessionLocal",
    "db_session",
    "async_bind",
    "async_dispose",
    "AsyncSessionLocal",
    "async_db_session",
]

_engine: Optional[Engine] = None
_async_engine: Optional[AsyncEngine] = None
SessionLocal: Optional[sessionmaker] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None

_ASYNC_SCHEMES = {
    "postgres://": "postgresql+asyncpg://",
    "postgresql://": "postgresql+asyncpg://",
    "postgresql+psycopg2://": "postgresql+asyncpg://",
    "sqlite://": "sqlite+aiosqlite://",
}


def _on_connect(dbapi_conn, _):
    # `int(...)` validates each value before interpolation — guards against
    # poisoned envvars (compromised secret store) injecting arbitrary SQL.
    stmt_ms = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "5000"))
    lock_ms = int(os.getenv("DB_LOCK_TIMEOUT_MS", "2000"))
    idle_ms = int(os.getenv("DB_IDLE_IN_TX_TIMEOUT_MS", "10000"))
    cur = dbapi_conn.cursor()
    try:
        cur.execute(
            f"SET statement_timeout = {stmt_ms};"
            f"SET lock_timeout = {lock_ms};"
            f"SET idle_in_transaction_session_timeout = {idle_ms}"
        )
    finally:
        cur.close()


def _engine_args(url):
    kwargs = {"echo": os.getenv("DB_ECHO", "").lower() in ("1", "true", "yes")}
    if not (url and url.startswith("postgresql")):
        return kwargs, {}
    kwargs.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "10")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
        pool_use_lifo=True,
    )
    return kwargs, {
        "application_name": os.getenv("K_SERVICE")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("APP_NAME", "serpens"),
        "connect_timeout": 5,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 3,
    }


def _normalize_sync_url(url):
    if url and url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url.removeprefix("postgres://")
    return url


def _normalize_async_url(url):
    if not url:
        return url
    for prefix, target in _ASYNC_SCHEMES.items():
        if url.startswith(prefix):
            return target + url.removeprefix(prefix)
    return url


def bind(url: Optional[str] = None) -> Engine:
    """Initialize the sync `Engine` and `SessionLocal`. Idempotent without `url`."""
    global _engine, SessionLocal
    if _engine is not None and url is None:
        return _engine
    if _engine is not None:
        _engine.dispose()
        _engine = SessionLocal = None

    url = _normalize_sync_url(url or envvars.get("DATABASE_URL"))
    kwargs, connect_args = _engine_args(url)
    _engine = create_engine(url, connect_args=connect_args, **kwargs)
    if url and url.startswith("postgresql"):
        event.listen(_engine, "connect", _on_connect)
    SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def dispose() -> None:
    global _engine, SessionLocal
    if _engine is None:
        return
    _engine.dispose()
    _engine = SessionLocal = None


def async_bind(url: Optional[str] = None) -> AsyncEngine:
    global _async_engine, AsyncSessionLocal
    if _async_engine is not None and url is None:
        return _async_engine
    if _async_engine is not None:
        asyncio.run(_async_engine.dispose())
        _async_engine = AsyncSessionLocal = None

    resolved = _normalize_async_url(url or envvars.get("DATABASE_URL"))
    kwargs, _ = _engine_args(resolved)
    _async_engine = create_async_engine(resolved, **kwargs)
    if resolved and resolved.startswith("postgresql"):
        # Async engines route DBAPI events through the underlying sync engine.
        event.listen(_async_engine.sync_engine, "connect", _on_connect)
    AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
    )
    return _async_engine


async def async_dispose() -> None:
    global _async_engine, AsyncSessionLocal
    if _async_engine is None:
        return
    await _async_engine.dispose()
    _async_engine = AsyncSessionLocal = None


@contextmanager
def db_session() -> Iterator[Session]:
    """Open a `Session`, commit on success, rollback on exception, close always.

    Auto-binds with `bind()` if no engine is configured. Convenient for Lambda
    handlers and short scripts; FastAPI handlers should prefer
    `Depends(SessionLocal)` so the framework owns the lifecycle.
    """
    if SessionLocal is None:
        bind()
    sess = SessionLocal()
    try:
        yield sess
        sess.commit()
    except BaseException:
        sess.rollback()
        raise
    finally:
        sess.close()


@asynccontextmanager
async def async_db_session() -> AsyncIterator[AsyncSession]:
    """Async counterpart of :func:`db_session`."""
    if AsyncSessionLocal is None:
        async_bind()
    sess = AsyncSessionLocal()
    try:
        yield sess
        await sess.commit()
    except BaseException:
        await sess.rollback()
        raise
    finally:
        await sess.close()


class Base(DeclarativeBase):
    """Default `DeclarativeBase`. Use `declarative_base(schema=...)` if you want a schema."""

    pass


def declarative_base(schema: Optional[str] = None):
    """Return a fresh declarative base, optionally bound to a Postgres schema."""
    if schema is None:
        return type("_Base", (DeclarativeBase,), {})
    return type("_Base", (DeclarativeBase,), {"metadata": MetaData(schema=schema)})


class TimestampMixin:
    """Adds `created_at` / `updated_at`; refreshes `updated_at` on every UPDATE."""

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
