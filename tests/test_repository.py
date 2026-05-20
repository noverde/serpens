import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import Integer, String, select
from sqlalchemy.orm import Mapped, mapped_column

from serpens import database
from serpens.database import Base
from serpens.database.repository import AsyncRepository, NotFound, Repository


class _Widget(Base):
    __tablename__ = "widget"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    slug: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class WidgetRepo(Repository[_Widget]):
    model = _Widget


class AsyncWidgetRepo(AsyncRepository[_Widget]):
    model = _Widget


def _seed(sess):
    for name, slug in [("foo", "a"), ("bar", "b"), ("baz", "c"), ("qux", "d")]:
        sess.add(_Widget(name=name, slug=slug))
    sess.flush()


class TestSyncRepository(unittest.TestCase):
    def setUp(self):
        database.dispose()
        self.engine = database.bind("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.sess = database.SessionLocal()
        _seed(self.sess)

    def tearDown(self):
        self.sess.close()
        database.dispose()

    def test_get_returns_row_or_none(self):
        repo = WidgetRepo(self.sess)
        self.assertEqual(repo.get(1).slug, "a")
        self.assertIsNone(repo.get(999))

    def test_get_or_raise(self):
        repo = WidgetRepo(self.sess)
        self.assertEqual(repo.get_or_raise(1).slug, "a")
        with self.assertRaises(NotFound):
            repo.get_or_raise(999)

    def test_get_by(self):
        repo = WidgetRepo(self.sess)
        self.assertEqual(repo.get_by(slug="b").name, "bar")
        self.assertIsNone(repo.get_by(slug="missing"))

    def test_exists_and_count(self):
        repo = WidgetRepo(self.sess)
        self.assertTrue(repo.exists(slug="a"))
        self.assertFalse(repo.exists(slug="zzz"))
        self.assertEqual(repo.count(), 4)
        self.assertEqual(repo.count(slug="a"), 1)

    def test_list_with_filters_order_limit_offset(self):
        repo = WidgetRepo(self.sess)
        rows = repo.list(order_by=_Widget.slug, limit=2, offset=1)
        self.assertEqual([r.slug for r in rows], ["b", "c"])
        self.assertEqual(
            repo.list(name="bar"), [self.sess.scalars(select(_Widget).filter_by(name="bar")).one()]
        )

    def test_paginate_returns_rows_and_total(self):
        repo = WidgetRepo(self.sess)
        rows, total = repo.paginate(page=1, size=2)
        self.assertEqual(len(rows), 2)
        self.assertEqual(total, 4)

        rows, total = repo.paginate(repo.query.order_by(_Widget.slug), page=2, size=2)
        self.assertEqual([r.slug for r in rows], ["c", "d"])
        self.assertEqual(total, 4)

    def test_paginate_rejects_zero(self):
        repo = WidgetRepo(self.sess)
        with self.assertRaises(ValueError):
            repo.paginate(page=0, size=10)
        with self.assertRaises(ValueError):
            repo.paginate(page=1, size=0)

    def test_add_flushes_and_returns_id(self):
        repo = WidgetRepo(self.sess)
        obj = repo.add(_Widget(name="new", slug="z"))
        self.assertIsNotNone(obj.id)

    def test_bulk_add(self):
        repo = WidgetRepo(self.sess)
        objs = repo.bulk_add([_Widget(name="m", slug="m1"), _Widget(name="n", slug="n1")])
        self.assertEqual(len(objs), 2)
        for o in objs:
            self.assertIsNotNone(o.id)

    def test_query_property_is_composable(self):
        repo = WidgetRepo(self.sess)
        stmt = repo.query.where(_Widget.name.in_(["foo", "bar"])).order_by(_Widget.slug)
        rows = self.sess.scalars(stmt).all()
        self.assertEqual([r.slug for r in rows], ["a", "b"])


class TestAsyncRepository(unittest.IsolatedAsyncioTestCase):
    """AsyncRepository against aiosqlite."""

    async def asyncSetUp(self):
        database.dispose()
        database._async_engine = None
        database.AsyncSessionLocal = None
        database.async_bind("sqlite+aiosqlite:///:memory:")
        async with database._async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def asyncTearDown(self):
        await database.async_dispose()

    async def test_async_crud_round_trip(self):
        async with database.AsyncSessionLocal() as sess:
            repo = AsyncWidgetRepo(sess)
            obj = await repo.add(_Widget(name="async-1", slug="a-1"))
            self.assertIsNotNone(obj.id)

            fetched = await repo.get(obj.id)
            self.assertEqual(fetched.slug, "a-1")

            self.assertTrue(await repo.exists(slug="a-1"))
            self.assertEqual(await repo.count(slug="a-1"), 1)

            with self.assertRaises(NotFound):
                await repo.get_or_raise(99999)

    async def test_async_get_by_and_list(self):
        async with database.AsyncSessionLocal() as sess:
            repo = AsyncWidgetRepo(sess)
            await repo.bulk_add([_Widget(name="foo", slug="a"), _Widget(name="bar", slug="b")])

            self.assertEqual((await repo.get_by(slug="a")).name, "foo")
            self.assertIsNone(await repo.get_by(slug="missing"))

            rows = await repo.list(order_by=_Widget.slug)
            self.assertEqual([r.slug for r in rows], ["a", "b"])

    async def test_async_paginate(self):
        async with database.AsyncSessionLocal() as sess:
            repo = AsyncWidgetRepo(sess)
            await repo.bulk_add([_Widget(name=f"n{i}", slug=f"s{i}") for i in range(5)])
            rows, total = await repo.paginate(repo.query.order_by(_Widget.slug), page=2, size=2)
            self.assertEqual(total, 5)
            self.assertEqual(len(rows), 2)


class TestUpsert(unittest.TestCase):
    """Postgres dialect required — exercised via mocked session."""

    def test_sync_upsert_builds_on_conflict_do_update(self):
        sess = MagicMock()
        sess.scalars.return_value.one.return_value = MagicMock(id=42)
        repo = WidgetRepo(sess)

        with patch("serpens.database.repository.pg_insert") as pgi:
            chain = pgi.return_value.values.return_value
            chain.on_conflict_do_update.return_value.returning.return_value = "STMT"
            result = repo.upsert(
                {"slug": "x", "name": "y"},
                conflict_on=["slug"],
                update_fields=["name"],
            )

        pgi.assert_called_once_with(_Widget)
        pgi.return_value.values.assert_called_once_with(slug="x", name="y")
        pgi.return_value.values.return_value.on_conflict_do_update.assert_called_once()
        sess.scalars.assert_called_once_with("STMT")
        self.assertEqual(result.id, 42)

    def test_sync_upsert_falls_back_to_do_nothing_when_no_update_fields(self):
        sess = MagicMock()
        sess.scalars.return_value.one.return_value = MagicMock()
        repo = WidgetRepo(sess)

        with patch("serpens.database.repository.pg_insert") as pgi:
            chain = pgi.return_value.values.return_value
            chain.on_conflict_do_nothing.return_value.returning.return_value = "STMT"
            repo.upsert({"slug": "x"}, conflict_on=["slug"])

        pgi.return_value.values.return_value.on_conflict_do_nothing.assert_called_once_with(
            index_elements=["slug"]
        )


if __name__ == "__main__":
    unittest.main()
