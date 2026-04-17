import asyncio
import os
from contextvars import ContextVar
from datetime import datetime
from functools import wraps
from typing import Tuple, TypeVar

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    bindparam,
    create_engine,
    delete,
    desc,
    event,
    func,
    insert,
    select,
    text,
    update,
)
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session,
    contains_eager,
    joinedload,
    mapped_column,
    relationship,
    selectinload,
    sessionmaker,
)

from serpens import envvars


__all__ = [
    # core session API (kept for backward compatibility)
    "Base",
    "EntityMixin",
    "TimestampMixin",
    "bind",
    "current_session",
    "db_session",
    "dispose",
    "bulk_insert",
    # async API
    "async_bind",
    "async_db_session",
    "async_dispose",
    "current_async_session",
    # sqlalchemy re-exports
    "Boolean",
    "Column",
    "Date",
    "DateTime",
    "ForeignKey",
    "Integer",
    "Mapped",
    "Numeric",
    "String",
    "Text",
    "UniqueConstraint",
    "bindparam",
    "contains_eager",
    "delete",
    "desc",
    "func",
    "insert",
    "joinedload",
    "mapped_column",
    "relationship",
    "select",
    "selectinload",
    "text",
    "update",
]


_engine = None
_SessionLocal = None
_async_engine = None
_AsyncSessionLocal = None


def _app_name():
    return (
        os.getenv("K_SERVICE")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("APP_NAME", "serpens")
    )


def _on_connect(dbapi_connection, _):
    stmt_timeout = int(os.getenv("DB_STATEMENT_TIMEOUT_MS", "5000"))
    lock_timeout = int(os.getenv("DB_LOCK_TIMEOUT_MS", "2000"))
    idle_tx = int(os.getenv("DB_IDLE_IN_TX_TIMEOUT_MS", "10000"))
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute(f"SET statement_timeout = {stmt_timeout}")
        cursor.execute(f"SET lock_timeout = {lock_timeout}")
        cursor.execute(f"SET idle_in_transaction_session_timeout = {idle_tx}")
    finally:
        cursor.close()


def _is_postgres(url):
    return bool(url) and url.startswith("postgresql")


def _pool_kwargs(url):
    kwargs = {
        "echo": os.getenv("DB_ECHO", "").lower() in ("1", "true", "yes"),
    }
    connect_args = {}

    if _is_postgres(url):
        kwargs.update(
            {
                "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
                "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
                "pool_timeout": int(os.getenv("DB_POOL_TIMEOUT", "10")),
                "pool_recycle": int(os.getenv("DB_POOL_RECYCLE", "1800")),
                "pool_pre_ping": True,
                "pool_use_lifo": True,
            }
        )
        connect_args = {
            "application_name": _app_name(),
            "connect_timeout": 5,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 3,
        }

    return kwargs, connect_args


def bind(url=None):
    global _engine, _SessionLocal
    if _engine is not None and url is None:
        return _engine
    if _engine is not None:
        _engine.dispose()
        _engine = None
        _SessionLocal = None

    url = url or envvars.get("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = "postgresql+psycopg2://" + url.removeprefix("postgres://")

    kwargs, connect_args = _pool_kwargs(url)
    _engine = create_engine(url, connect_args=connect_args, **kwargs)
    if _is_postgres(url):
        event.listen(_engine, "connect", _on_connect)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def dispose():
    global _engine, _SessionLocal
    if _engine is None:
        return
    _engine.dispose()
    _engine = None
    _SessionLocal = None


def _async_url(url):
    if url and url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgres://")
    elif url and url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql://")
    elif url and url.startswith("postgresql+psycopg2://"):
        url = "postgresql+asyncpg://" + url.removeprefix("postgresql+psycopg2://")
    elif url and url.startswith("sqlite://"):
        url = "sqlite+aiosqlite://" + url.removeprefix("sqlite://")
    return url


def async_bind(url=None):
    global _async_engine, _AsyncSessionLocal
    if _async_engine is not None and url is None:
        return _async_engine
    if _async_engine is not None:
        asyncio.run(_async_engine.dispose())
        _async_engine = None
        _AsyncSessionLocal = None

    url = _async_url(url or envvars.get("DATABASE_URL"))
    kwargs, _ = _pool_kwargs(url)
    _async_engine = create_async_engine(url, **kwargs)
    _AsyncSessionLocal = async_sessionmaker(
        bind=_async_engine, expire_on_commit=False, autoflush=False, class_=AsyncSession
    )
    return _async_engine


async def async_dispose():
    global _async_engine, _AsyncSessionLocal
    if _async_engine is None:
        return
    await _async_engine.dispose()
    _async_engine = None
    _AsyncSessionLocal = None


T = TypeVar("T")
_Frame = Tuple[Session, bool]
_AsyncFrame = Tuple[AsyncSession, bool]
_stack_var: ContextVar[Tuple[_Frame, ...]] = ContextVar("_db_session_stack", default=())
_async_stack_var: ContextVar[Tuple[_AsyncFrame, ...]] = ContextVar(
    "_async_db_session_stack", default=()
)


def current_session():
    stack = _stack_var.get()
    return stack[-1][0] if stack else None


def current_async_session():
    stack = _async_stack_var.get()
    return stack[-1][0] if stack else None


class _DbSession:
    def __call__(self, fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            with self:
                return fn(*args, **kwargs)

        return wrapper

    def __enter__(self):
        stack = _stack_var.get()
        if stack:
            session = stack[-1][0]
            _stack_var.set(stack + ((session, False),))
            return session

        if _SessionLocal is None:
            bind()

        session = _SessionLocal()
        _stack_var.set(((session, True),))
        return session

    def __exit__(self, exc_type, *_):
        stack = _stack_var.get()
        if not stack:
            return

        session, is_owner = stack[-1]
        _stack_var.set(stack[:-1])

        if not is_owner:
            return

        try:
            if exc_type is None:
                session.commit()
            else:
                session.rollback()
        finally:
            session.close()


class _AsyncDbSession:
    def __call__(self, fn):
        @wraps(fn)
        async def wrapper(*args, **kwargs):
            async with self:
                return await fn(*args, **kwargs)

        return wrapper

    async def __aenter__(self):
        stack = _async_stack_var.get()
        if stack:
            session = stack[-1][0]
            _async_stack_var.set(stack + ((session, False),))
            return session

        if _AsyncSessionLocal is None:
            async_bind()

        session = _AsyncSessionLocal()
        _async_stack_var.set(((session, True),))
        return session

    async def __aexit__(self, exc_type, *_):
        stack = _async_stack_var.get()
        if not stack:
            return

        session, is_owner = stack[-1]
        _async_stack_var.set(stack[:-1])

        if not is_owner:
            return

        try:
            if exc_type is None:
                await session.commit()
            else:
                await session.rollback()
        finally:
            await session.close()


db_session = _DbSession()
async_db_session = _AsyncDbSession()


class Base(DeclarativeBase):
    pass


class _SelectQuery:
    def __init__(self, entity, **filters):
        self._entity = entity
        self._filters = filters
        self._order = None

    def _stmt(self):
        stmt = select(self._entity).filter_by(**self._filters)
        return stmt.order_by(*self._order) if self._order else stmt

    def order_by(self, *cols):
        self._order = cols
        return self

    def first(self):
        with db_session as sess:
            return sess.scalars(self._stmt()).first()

    def all(self):
        with db_session as sess:
            return list(sess.scalars(self._stmt()).all())

    def delete(self):
        with db_session as sess:
            return sess.execute(delete(self._entity).filter_by(**self._filters)).rowcount

    def __iter__(self):
        return iter(self.all())


class EntityMixin:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        sess = current_session()
        if sess is None:
            raise RuntimeError(
                "cannot instantiate {} outside an active db_session".format(type(self).__name__)
            )
        sess.add(self)
        sess.flush()

    @classmethod
    def get(cls, **kwargs):
        with db_session as sess:
            return sess.scalars(select(cls).filter_by(**kwargs)).first()

    @classmethod
    def select(cls, **kwargs):
        return _SelectQuery(cls, **kwargs)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )


def bulk_insert(entity_cls, mappings):
    with db_session as sess:
        sess.bulk_insert_mappings(entity_cls, list(mappings))
