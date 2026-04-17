import unittest
from unittest.mock import MagicMock, patch

from sqlalchemy import Column, Integer, String

from serpens import database
from serpens.database import Base, EntityMixin, current_session, db_session


class _Item(EntityMixin, Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


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
