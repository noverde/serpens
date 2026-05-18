"""Generic Repository[T] / AsyncRepository[T] over SQLAlchemy 2.0.

Thin base: PK lookups, filtered queries, paginate, add/bulk_add, upsert.
Hard delete and partial update are *not* exposed — services do soft-delete
or optimistic-locked updates differently. Subclass and add what you need;
fall back to ``self.query`` (a ``Select[tuple[T]]``) for anything custom.
"""

from typing import Any, Generic, Iterable, List, Optional, Sequence, Tuple, Type, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Session

T = TypeVar("T", bound=DeclarativeBase)

__all__ = ["NotFound", "Repository", "AsyncRepository"]


class NotFound(Exception):
    pass


def _upsert_stmt(model, values, conflict_on, update_fields):
    stmt = pg_insert(model).values(**values)
    if update_fields is None:
        update_fields = [k for k in values.keys() if k not in conflict_on]
    if update_fields:
        stmt = stmt.on_conflict_do_update(
            index_elements=list(conflict_on),
            set_={f: stmt.excluded[f] for f in update_fields},
        )
    else:
        stmt = stmt.on_conflict_do_nothing(index_elements=list(conflict_on))
    return stmt.returning(model)


class Repository(Generic[T]):
    model: Type[T]

    def __init__(self, sess: Session):
        self.sess = sess

    @property
    def query(self) -> Select:
        return select(self.model)

    def get(self, id_: Any) -> Optional[T]:
        return self.sess.get(self.model, id_)

    def get_or_raise(self, id_: Any) -> T:
        obj = self.get(id_)
        if obj is None:
            raise NotFound(f"{self.model.__name__} id={id_!r}")
        return obj

    def get_by(self, **filters) -> Optional[T]:
        return self.sess.scalars(self.query.filter_by(**filters)).first()

    def exists(self, **filters) -> bool:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return bool(self.sess.scalar(stmt))

    def count(self, **filters) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return self.sess.scalar(stmt) or 0

    def list(
        self,
        *,
        order_by: Any = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters,
    ) -> List[T]:
        stmt = self.query.filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        return list(self.sess.scalars(stmt).all())

    def paginate(
        self,
        stmt: Optional[Select] = None,
        *,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[T], int]:
        if page < 1 or size < 1:
            raise ValueError("page and size must be >= 1")
        stmt = stmt if stmt is not None else self.query
        total = self.sess.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = self.sess.scalars(stmt.offset((page - 1) * size).limit(size)).all()
        return list(rows), total

    def add(self, obj: T, *, flush: bool = True) -> T:
        self.sess.add(obj)
        if flush:
            self.sess.flush()
        return obj

    def bulk_add(self, objs: Iterable[T], *, flush: bool = True) -> Sequence[T]:
        objs = list(objs)
        self.sess.add_all(objs)
        if flush:
            self.sess.flush()
        return objs

    def upsert(
        self,
        values: dict,
        *,
        conflict_on: Sequence[str],
        update_fields: Optional[Sequence[str]] = None,
    ) -> T:
        """Postgres ``INSERT ... ON CONFLICT`` returning the row. The right
        primitive for idempotent inserts — no race window like get-or-create.
        """
        stmt = _upsert_stmt(self.model, values, conflict_on, update_fields)
        return self.sess.scalars(stmt).one()


class AsyncRepository(Generic[T]):
    model: Type[T]

    def __init__(self, sess: AsyncSession):
        self.sess = sess

    @property
    def query(self) -> Select:
        return select(self.model)

    async def get(self, id_: Any) -> Optional[T]:
        return await self.sess.get(self.model, id_)

    async def get_or_raise(self, id_: Any) -> T:
        obj = await self.get(id_)
        if obj is None:
            raise NotFound(f"{self.model.__name__} id={id_!r}")
        return obj

    async def get_by(self, **filters) -> Optional[T]:
        return (await self.sess.scalars(self.query.filter_by(**filters))).first()

    async def exists(self, **filters) -> bool:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return bool(await self.sess.scalar(stmt))

    async def count(self, **filters) -> int:
        stmt = select(func.count()).select_from(self.model).filter_by(**filters)
        return (await self.sess.scalar(stmt)) or 0

    async def list(
        self,
        *,
        order_by: Any = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        **filters,
    ) -> List[T]:
        stmt = self.query.filter_by(**filters)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        if limit is not None:
            stmt = stmt.limit(limit)
        if offset is not None:
            stmt = stmt.offset(offset)
        return list((await self.sess.scalars(stmt)).all())

    async def paginate(
        self,
        stmt: Optional[Select] = None,
        *,
        page: int = 1,
        size: int = 20,
    ) -> Tuple[List[T], int]:
        if page < 1 or size < 1:
            raise ValueError("page and size must be >= 1")
        stmt = stmt if stmt is not None else self.query
        total = await self.sess.scalar(select(func.count()).select_from(stmt.subquery())) or 0
        rows = (await self.sess.scalars(stmt.offset((page - 1) * size).limit(size))).all()
        return list(rows), total

    async def add(self, obj: T, *, flush: bool = True) -> T:
        self.sess.add(obj)
        if flush:
            await self.sess.flush()
        return obj

    async def bulk_add(self, objs: Iterable[T], *, flush: bool = True) -> Sequence[T]:
        objs = list(objs)
        self.sess.add_all(objs)
        if flush:
            await self.sess.flush()
        return objs

    async def upsert(
        self,
        values: dict,
        *,
        conflict_on: Sequence[str],
        update_fields: Optional[Sequence[str]] = None,
    ) -> T:
        """Postgres ``INSERT ... ON CONFLICT`` returning the row."""
        stmt = _upsert_stmt(self.model, values, conflict_on, update_fields)
        return (await self.sess.scalars(stmt)).one()
