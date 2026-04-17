import os
from contextvars import ContextVar
from functools import wraps
from typing import Tuple, TypeVar

from sqlalchemy import create_engine, desc, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from serpens import envvars


__all__ = [
    "Base",
    "EntityMixin",
    "bind",
    "current_session",
    "db_session",
    "desc",
    "dispose",
]


_engine = None
_SessionLocal = None


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

    _engine = create_engine(url, connect_args=connect_args, **kwargs)
    if _is_postgres(url):
        event.listen(_engine, "connect", _on_connect)
    _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, autoflush=False)
    return _engine


def _is_postgres(url):
    return bool(url) and url.startswith("postgresql")


def dispose():
    global _engine, _SessionLocal
    if _engine is None:
        return
    _engine.dispose()
    _engine = None
    _SessionLocal = None


T = TypeVar("T")
_Frame = Tuple[Session, bool]
_stack_var: ContextVar[Tuple[_Frame, ...]] = ContextVar("_db_session_stack", default=())


def current_session():
    stack = _stack_var.get()
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


db_session = _DbSession()


class Base(DeclarativeBase):
    pass


class _SelectQuery:
    def __init__(self, entity, **filters):
        self._entity = entity
        self._filters = filters
        self._order = None

    def _q(self, sess):
        q = sess.query(self._entity).filter_by(**self._filters)
        return q.order_by(*self._order) if self._order else q

    def order_by(self, *cols):
        self._order = cols
        return self

    def first(self):
        with db_session as sess:
            return self._q(sess).first()

    def all(self):
        with db_session as sess:
            return self._q(sess).all()

    def delete(self):
        with db_session as sess:
            return self._q(sess).delete(synchronize_session=False)

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
            return sess.query(cls).filter_by(**kwargs).first()

    @classmethod
    def select(cls, **kwargs):
        return _SelectQuery(cls, **kwargs)

    def to_dict(self):
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
