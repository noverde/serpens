import asyncio
import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import Column, Integer, String

from serpens import database
from serpens.database import (
    Base,
    EntityMixin,
    TimestampMixin,
    async_db_session,
    bulk_insert,
    current_async_session,
    current_session,
    db_session,
    select,
)


class _Item(EntityMixin, Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class _Stamped(EntityMixin, TimestampMixin, Base):
    __tablename__ = "stamped"

    id = Column(Integer, primary_key=True, autoincrement=True)
    label = Column(String, nullable=False)


class TestDatabase(unittest.TestCase):
    def setUp(self):
        database.dispose()

        self.engine = database.bind("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)

    def tearDown(self):
        database.dispose()

    def test_current_session_outside_scope_is_none(self):
        self.assertIsNone(current_session())

    def test_db_session_context_manager_commits(self):
        with db_session as sess:
            self.assertIsNotNone(sess)
            self.assertIs(current_session(), sess)

        self.assertIsNone(current_session())

    def test_db_session_nested_reuses_session(self):
        with db_session as outer:
            with db_session as inner:
                self.assertIs(outer, inner)

        self.assertIsNone(current_session())

    def test_db_session_decorator(self):
        captured = {}

        @db_session
        def handler():
            captured["session"] = current_session()

        handler()

        self.assertIsNotNone(captured["session"])
        self.assertIsNone(current_session())

    def test_db_session_rollback_on_exception(self):
        with self.assertRaises(ValueError):
            with db_session:
                _Item(name="fail")
                raise ValueError("boom")

        with db_session as sess:
            self.assertEqual(sess.query(_Item).count(), 0)

    def test_entity_mixin_requires_active_session(self):
        with self.assertRaises(RuntimeError):
            _Item(name="orphan")

    def test_entity_mixin_persists_in_session(self):
        with db_session:
            item = _Item(name="foo")
            self.assertIsNotNone(item.id)

        with db_session as sess:
            persisted = sess.query(_Item).filter_by(name="foo").first()
            self.assertIsNotNone(persisted)

    def test_entity_mixin_get(self):
        with db_session:
            _Item(name="foo")

        result = _Item.get(name="foo")
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "foo")

    def test_entity_mixin_select_first(self):
        with db_session:
            _Item(name="a")
            _Item(name="b")

        result = _Item.select(name="a").first()
        self.assertIsNotNone(result)
        self.assertEqual(result.name, "a")

    def test_entity_mixin_select_all(self):
        with db_session:
            _Item(name="a")
            _Item(name="b")

        result = _Item.select().all()
        self.assertEqual(len(result), 2)

    def test_entity_mixin_select_iter(self):
        with db_session:
            _Item(name="a")
            _Item(name="b")

        names = sorted(i.name for i in _Item.select())
        self.assertEqual(names, ["a", "b"])

    def test_entity_mixin_select_delete(self):
        with db_session:
            _Item(name="a")
            _Item(name="b")

        _Item.select().delete()

        with db_session as sess:
            self.assertEqual(sess.query(_Item).count(), 0)

    def test_entity_mixin_to_dict(self):
        with db_session:
            item = _Item(name="foo")
            result = item.to_dict()

        self.assertEqual(result["name"], "foo")
        self.assertIn("id", result)

    def test_select_2_0_style_query(self):
        with db_session:
            _Item(name="foo")
            _Item(name="bar")

        with db_session as sess:
            stmt = select(_Item).where(_Item.name == "foo")
            row = sess.scalars(stmt).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.name, "foo")

    def test_timestamp_mixin_sets_timestamps(self):
        with db_session:
            item = _Stamped(label="hello")
            self.assertIsNotNone(item.created_at)
            self.assertIsNotNone(item.updated_at)

    def test_timestamp_mixin_on_update(self):
        with db_session:
            item = _Stamped(label="hello")
            original_updated = item.updated_at

        with db_session as sess:
            row = sess.query(_Stamped).filter_by(label="hello").first()
            row.label = "changed"
            sess.flush()
            self.assertGreaterEqual(row.updated_at, original_updated)

    def test_bulk_insert(self):
        bulk_insert(
            _Item,
            [{"name": "x"}, {"name": "y"}, {"name": "z"}],
        )

        with db_session as sess:
            self.assertEqual(sess.query(_Item).count(), 3)


class TestBindDispose(unittest.TestCase):
    def setUp(self):
        database.dispose()

    def tearDown(self):
        database.dispose()

    def test_bind_is_idempotent_without_url(self):
        engine1 = database.bind("sqlite:///:memory:")
        engine2 = database.bind()
        self.assertIs(engine1, engine2)

    def test_bind_rebinds_when_url_provided(self):
        engine1 = database.bind("sqlite:///:memory:")
        engine2 = database.bind("sqlite:///:memory:")
        self.assertIsNot(engine1, engine2)

    def test_bind_normalizes_postgres_scheme(self):
        with (
            patch("serpens.database.create_engine") as mcreate,
            patch("serpens.database.event"),
        ):
            mcreate.return_value = MagicMock()
            database.bind("postgres://user:pass@host/db")
            called_url = mcreate.call_args.args[0]
            self.assertTrue(called_url.startswith("postgresql+psycopg2://"))

    def test_dispose_noop_when_not_bound(self):
        database.dispose()
        self.assertIsNone(database._engine)

    def test_dispose_clears_engine(self):
        database.bind("sqlite:///:memory:")
        database.dispose()
        self.assertIsNone(database._engine)
        self.assertIsNone(database._SessionLocal)


class TestAsyncDatabase(unittest.TestCase):
    def setUp(self):
        database.dispose()
        self.engine = database.bind("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        database.async_bind("sqlite:///:memory:")

    def tearDown(self):
        asyncio.run(database.async_dispose())
        database.dispose()

    def test_current_async_session_outside_scope_is_none(self):
        async def run():
            return current_async_session()

        self.assertIsNone(asyncio.run(run()))

    def test_async_db_session_context_manager(self):
        async def run():
            async with async_db_session as sess:
                self.assertIsNotNone(sess)
                self.assertIs(current_async_session(), sess)
            self.assertIsNone(current_async_session())

        asyncio.run(run())

    def test_async_db_session_nested_reuses(self):
        async def run():
            async with async_db_session as outer:
                async with async_db_session as inner:
                    self.assertIs(outer, inner)

        asyncio.run(run())

    def test_async_db_session_decorator(self):
        captured = {}

        @async_db_session
        async def handler():
            captured["session"] = current_async_session()

        asyncio.run(handler())
        self.assertIsNotNone(captured["session"])

    def test_async_db_session_rollback_on_exception(self):
        async def run():
            with self.assertRaises(ValueError):
                async with async_db_session:
                    raise ValueError("boom")

        asyncio.run(run())
