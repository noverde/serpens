import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy import Column, Integer, String, select

from serpens import database
from serpens.database import (
    Base,
    TimestampMixin,
    async_db_session,
    db_session,
)


class _Item(Base):
    __tablename__ = "item"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)


class _Stamped(TimestampMixin, Base):
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

    def test_session_local_idiomatic(self):
        # SA 2.0 idiom: caller owns commit/rollback, no global state.
        with database.SessionLocal() as sess:
            sess.add(_Item(name="explicit"))
            sess.commit()

        with database.SessionLocal() as sess:
            row = sess.scalars(select(_Item).filter_by(name="explicit")).first()
            self.assertIsNotNone(row)

    def test_session_local_is_module_attribute(self):
        # After bind(), SessionLocal is exposed; before, it's None.
        self.assertIsNotNone(database.SessionLocal)
        database.dispose()
        self.assertIsNone(database.SessionLocal)

    def test_db_session_commits_on_success(self):
        with db_session() as sess:
            sess.add(_Item(name="auto"))

        with db_session() as sess:
            self.assertEqual(sess.query(_Item).count(), 1)

    def test_db_session_rolls_back_on_exception(self):
        with self.assertRaises(ValueError):
            with db_session() as sess:
                sess.add(_Item(name="fail"))
                raise ValueError("boom")

        with db_session() as sess:
            self.assertEqual(sess.query(_Item).count(), 0)

    def test_db_session_auto_binds_when_unconfigured(self):
        database.dispose()
        with patch.object(database, "envvars") as m_env:
            m_env.get.return_value = "sqlite:///:memory:"
            with db_session() as sess:
                self.assertIsNotNone(sess)

    def test_select_2_0_query(self):
        with db_session() as sess:
            sess.add(_Item(name="foo"))
            sess.add(_Item(name="bar"))

        with db_session() as sess:
            row = sess.scalars(select(_Item).where(_Item.name == "foo")).first()
            self.assertIsNotNone(row)
            self.assertEqual(row.name, "foo")

    def test_timestamp_mixin_sets_timestamps(self):
        with db_session() as sess:
            item = _Stamped(label="hello")
            sess.add(item)
            sess.flush()
            self.assertIsNotNone(item.created_at)
            self.assertIsNotNone(item.updated_at)

    def test_timestamp_mixin_on_update(self):
        with db_session() as sess:
            item = _Stamped(label="hello")
            sess.add(item)
            sess.flush()
            original_updated = item.updated_at

        with db_session() as sess:
            row = sess.query(_Stamped).filter_by(label="hello").first()
            row.label = "changed"
            sess.flush()
            self.assertGreaterEqual(row.updated_at, original_updated)


class TestStatementTimeout(unittest.TestCase):
    def test_sql_built_for_postgres(self):
        self.assertEqual(
            database._statement_timeout_sql("postgresql", 3000),
            "SET LOCAL statement_timeout = 3000",
        )

    def test_sql_none_for_non_postgres(self):
        self.assertIsNone(database._statement_timeout_sql("sqlite", 3000))

    def test_sql_none_when_timeout_unset(self):
        self.assertIsNone(database._statement_timeout_sql("postgresql", None))

    def test_sql_coerces_to_int(self):
        self.assertEqual(
            database._statement_timeout_sql("postgresql", "1500"),
            "SET LOCAL statement_timeout = 1500",
        )

    def test_sql_none_for_non_positive(self):
        self.assertIsNone(database._statement_timeout_sql("postgresql", 0))
        self.assertIsNone(database._statement_timeout_sql("postgresql", -100))

    def test_db_session_accepts_timeout_on_non_postgres(self):
        database.dispose()
        engine = database.bind("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        try:
            with db_session(statement_timeout_ms=3000) as sess:
                sess.add(_Item(name="x"))
            with db_session() as sess:
                self.assertEqual(len(sess.execute(select(_Item)).scalars().all()), 1)
        finally:
            database.dispose()

    def test_db_session_executes_set_local_for_postgres(self):
        mock_sess = MagicMock()
        engine = MagicMock()
        engine.dialect.name = "postgresql"
        with patch.object(database, "SessionLocal", MagicMock(return_value=mock_sess)):
            with patch.object(database, "_engine", engine):
                with db_session(statement_timeout_ms=2500):
                    pass

        executed_sql = str(mock_sess.execute.call_args[0][0])
        self.assertEqual(executed_sql, "SET LOCAL statement_timeout = 2500")

    def test_async_db_session_executes_set_local_for_postgres(self):
        mock_sess = MagicMock()
        mock_sess.execute = AsyncMock()
        mock_sess.commit = AsyncMock()
        mock_sess.close = AsyncMock()
        engine = MagicMock()
        engine.dialect.name = "postgresql"

        async def run():
            with patch.object(database, "AsyncSessionLocal", MagicMock(return_value=mock_sess)):
                with patch.object(database, "_async_engine", engine):
                    async with async_db_session(statement_timeout_ms=2500):
                        pass

        asyncio.run(run())

        mock_sess.execute.assert_awaited_once()
        executed_sql = str(mock_sess.execute.await_args[0][0])
        self.assertEqual(executed_sql, "SET LOCAL statement_timeout = 2500")

    def test_async_db_session_no_set_local_for_non_postgres(self):
        mock_sess = MagicMock()
        mock_sess.execute = AsyncMock()
        mock_sess.commit = AsyncMock()
        mock_sess.close = AsyncMock()
        engine = MagicMock()
        engine.dialect.name = "sqlite"

        async def run():
            with patch.object(database, "AsyncSessionLocal", MagicMock(return_value=mock_sess)):
                with patch.object(database, "_async_engine", engine):
                    async with async_db_session(statement_timeout_ms=2500):
                        pass

        asyncio.run(run())

        mock_sess.execute.assert_not_awaited()


class TestDeclarativeBaseFactory(unittest.TestCase):
    def test_no_schema(self):
        b = database.declarative_base()
        self.assertTrue(hasattr(b, "metadata"))

    def test_with_schema(self):
        b = database.declarative_base(schema="public")
        self.assertEqual(b.metadata.schema, "public")


class TestBindDispose(unittest.TestCase):
    def setUp(self):
        database.dispose()

    def tearDown(self):
        database.dispose()

    def test_bind_idempotent_without_url(self):
        engine1 = database.bind("sqlite:///:memory:")
        engine2 = database.bind()
        self.assertIs(engine1, engine2)

    def test_bind_rebinds_when_url_provided(self):
        engine1 = database.bind("sqlite:///:memory:")
        engine2 = database.bind("sqlite:///:memory:")
        self.assertIsNot(engine1, engine2)

    def test_bind_normalizes_postgres_scheme(self):
        with patch("serpens.database.create_engine") as mcreate, patch("serpens.database.event"):
            mcreate.return_value = MagicMock()
            database.bind("postgres://user:pass@host/db")
            called_url = mcreate.call_args.args[0]
            self.assertTrue(called_url.startswith("postgresql+psycopg2://"))

    def test_dispose_noop_when_not_bound(self):
        database.dispose()
        self.assertIsNone(database._engine)

    def test_dispose_clears_state(self):
        database.bind("sqlite:///:memory:")
        database.dispose()
        self.assertIsNone(database._engine)
        self.assertIsNone(database.SessionLocal)


class TestOnConnect(unittest.TestCase):
    """Postgres `_on_connect` listener applies timeouts safely."""

    def test_validates_envvars_with_int(self):
        with patch.dict("os.environ", {"DB_STATEMENT_TIMEOUT_MS": "1000;DROP TABLE x"}):
            cur = MagicMock()
            conn = MagicMock()
            conn.cursor.return_value = cur
            with self.assertRaises(ValueError):
                database._on_connect(conn, None)
            cur.execute.assert_not_called()

    def test_executes_set_statements(self):
        cur = MagicMock()
        conn = MagicMock()
        conn.cursor.return_value = cur
        with patch.dict(
            "os.environ",
            {
                "DB_STATEMENT_TIMEOUT_MS": "9000",
                "DB_LOCK_TIMEOUT_MS": "1500",
                "DB_IDLE_IN_TX_TIMEOUT_MS": "12000",
            },
        ):
            database._on_connect(conn, None)
        executed = [c.args[0] for c in cur.execute.call_args_list]
        self.assertEqual(len(executed), 3)
        self.assertEqual(executed[0], "SET statement_timeout = 9000")
        self.assertEqual(executed[1], "SET lock_timeout = 1500")
        self.assertEqual(executed[2], "SET idle_in_transaction_session_timeout = 12000")
        cur.close.assert_called_once()


class TestAsyncEngineRegistersOnConnect(unittest.TestCase):
    """Async engine must also receive the `_on_connect` timeout listener."""

    def tearDown(self):
        database._async_engine = None
        database.AsyncSessionLocal = None

    def test_postgres_registers_listener(self):
        with patch("serpens.database.create_async_engine") as mcreate, patch(
            "serpens.database.event"
        ) as mevent:
            mcreate.return_value = MagicMock()
            database.async_bind("postgresql://user:pw@host/db")
            mevent.listen.assert_called_once()
            args = mevent.listen.call_args.args
            self.assertEqual(args[1], "connect")
            self.assertIs(args[2], database._on_connect)

    def test_sqlite_does_not_register_listener(self):
        with patch("serpens.database.create_async_engine") as mcreate, patch(
            "serpens.database.event"
        ) as mevent:
            mcreate.return_value = MagicMock()
            database.async_bind("sqlite:///:memory:")
            mevent.listen.assert_not_called()


class TestAsyncDatabase(unittest.TestCase):
    def setUp(self):
        database.dispose()
        self.engine = database.bind("sqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        database.async_bind("sqlite:///:memory:")

    def tearDown(self):
        asyncio.run(database.async_dispose())
        database.dispose()

    def test_async_db_session_commits(self):
        async def run():
            async with async_db_session() as sess:
                self.assertIsNotNone(sess)

        asyncio.run(run())

    def test_async_db_session_rollback_on_exception(self):
        async def run():
            with self.assertRaises(ValueError):
                async with async_db_session():
                    raise ValueError("boom")

        asyncio.run(run())
