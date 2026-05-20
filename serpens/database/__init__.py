"""Thin SQLAlchemy 2.0 layer: engine, session factory, declarative base.

Sync and async APIs mirror each other. Queries use `sqlalchemy` directly.
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
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, sessionmaker

from serpens import envvars
from serpens.database.repository import AsyncRepository, NotFound, Repository

__all__ = [
    "Base",
    "TimestampMixin",
    "declarative_base",
    "bind",
    "dispose",
    "SessionLocal",
    "db_session",
    "fastapi_session",
    "async_bind",
    "async_dispose",
    "AsyncSessionLocal",
    "async_db_session",
    "fastapi_async_session",
    "Repository",
    "AsyncRepository",
    "NotFound",
]

_engine: Optional[Engine] = None
_async_engine: Optional[AsyncEngine] = None
SessionLocal: Optional[sessionmaker] = None
AsyncSessionLocal: Optional[async_sessionmaker] = None


def _on_connect(dbapi_conn, _):
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


def _engine_args(url, pool_use_lifo=None):
    kwargs = {"echo": os.getenv("DB_ECHO", "").lower() in ("1", "true", "yes")}
    if not (url and url.startswith("postgresql")):
        return kwargs, {}
    if pool_use_lifo is None:
        pool_use_lifo = os.getenv("DB_POOL_USE_LIFO", "true").lower() in ("1", "true", "yes")
    kwargs.update(
        pool_size=int(os.getenv("DB_POOL_SIZE", "10")),
        max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "20")),
        pool_timeout=int(os.getenv("DB_POOL_TIMEOUT", "10")),
        pool_recycle=int(os.getenv("DB_POOL_RECYCLE", "1800")),
        pool_pre_ping=True,
        pool_use_lifo=pool_use_lifo,
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
        return url.replace("postgres://", "postgresql+psycopg2://", 1)
    return url


_ASYNC_SCHEMES = {
    "postgres://": "postgresql+asyncpg://",
    "postgresql://": "postgresql+asyncpg://",
    "postgresql+psycopg2://": "postgresql+asyncpg://",
    "sqlite://": "sqlite+aiosqlite://",
}


def _normalize_async_url(url):
    if not url:
        return url
    for prefix, target in _ASYNC_SCHEMES.items():
        if url.startswith(prefix):
            return url.replace(prefix, target, 1)
    return url


def bind(url: Optional[str] = None, pool_use_lifo: Optional[bool] = None) -> Engine:
    global _engine, SessionLocal
    if _engine is not None and url is None:
        return _engine
    if _engine is not None:
        _engine.dispose()
        _engine = SessionLocal = None

    url = _normalize_sync_url(url or envvars.get("DATABASE_URL"))
    kwargs, connect_args = _engine_args(url, pool_use_lifo=pool_use_lifo)
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


def async_bind(url: Optional[str] = None, pool_use_lifo: Optional[bool] = None) -> AsyncEngine:
    global _async_engine, AsyncSessionLocal
    if _async_engine is not None and url is None:
        return _async_engine
    if _async_engine is not None:
        asyncio.run(_async_engine.dispose())
        _async_engine = AsyncSessionLocal = None

    resolved = _normalize_async_url(url or envvars.get("DATABASE_URL"))
    kwargs, _ = _engine_args(resolved, pool_use_lifo=pool_use_lifo)
    _async_engine = create_async_engine(resolved, **kwargs)
    if resolved and resolved.startswith("postgresql"):
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


def fastapi_session() -> Iterator[Session]:
    with db_session() as sess:
        yield sess


async def fastapi_async_session() -> AsyncIterator[AsyncSession]:
    async with async_db_session() as sess:
        yield sess


class Base(DeclarativeBase):
    pass


def declarative_base(schema: Optional[str] = None):
    if schema is None:
        return type("_Base", (DeclarativeBase,), {})
    return type("_Base", (DeclarativeBase,), {"metadata": MetaData(schema=schema)})


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )
