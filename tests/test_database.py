import unittest

from pony.orm.core import db_session

from serpens import database


def test_migrate():
    database_url = "sqlite:///serpens/test.db"
    path = "./tests/samples/migrations"
    database.migrate(database_url, path)


class TestDatabase(unittest.TestCase):
    def test_get_connection_postgres(self):
        dsn = "postgres://postgres:postgres@postgres/postgres"
        result = database.get_connection(dsn)
        self.assertEqual(result, ["postgres", dsn])

    def test_get_connection_sqlite(self):
        result = database.get_connection("sqlite://test.db")
        self.assertEqual(result, ["sqlite", "test.db"])

    def test_get_connection_sqlite_memory(self):
        result = database.get_connection("sqlite://:memory:")
        self.assertEqual(result, ["sqlite", ":memory:"])

    @db_session
    def test_database_setup(self):
        db = database.setup("sqlite://:memory:")
        db.execute("CREATE TABLE foo (id int, bar text)")
        db.execute("INSERT INTO foo (id, bar) VALUES (1, 'test')")

        result = db.get("SELECT * FROM foo WHERE id = 1")

        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.bar, "test")
