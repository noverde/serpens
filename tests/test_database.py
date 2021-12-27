import os
import unittest

from unittest.mock import patch

from pony.orm.core import db_session, PrimaryKey, Required

from serpens.database import Database


class TestDatabase(unittest.TestCase):
    def test_parse_uri_postgres(self):
        uri = "postgres://postgres:postgres@postgres/postgres"
        result = Database._parse_uri(uri)
        self.assertEqual(result, ("postgres", uri))

    def test_parse_uri_sqlite(self):
        result = Database._parse_uri("sqlite://test.db")
        self.assertEqual(result, ("sqlite", "test.db"))

    def test_parse_uri_sqlite_memory(self):
        result = Database._parse_uri("sqlite://:memory:")
        self.assertEqual(result, ("sqlite", ":memory:"))

    def test_parse_uri_empty_uri(self):
        with self.assertRaises(ValueError):
            Database._parse_uri("")

    def test_parse_uri_invalid_uri(self):
        with self.assertRaises(ValueError):
            Database._parse_uri("xxx")

    @db_session
    def test_database_instance(self):
        db = Database("sqlite://:memory:")
        db.execute("CREATE TABLE foo (id int, bar text)")
        db.execute("INSERT INTO foo (id, bar) VALUES (1, 'test')")

        result = db.get("SELECT * FROM foo WHERE id = 1")

        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.bar, "test")

    def test_database_instance_no_uri(self):
        db = Database()
        self.assertIsInstance(db, Database)

    def test_database_instance_empty_uri(self):
        with self.assertRaises(ValueError):
            Database("")

    def test_database_instance_invalid_uri(self):
        with self.assertRaises(ValueError):
            Database("xxx")

    @db_session
    def test_database_bind(self):
        db = Database()
        self.assertIsInstance(db, Database)

        db.bind("sqlite://:memory:")
        result = db.get("SELECT 1")
        self.assertEqual(result, 1)

    @db_session
    def test_database_bind_exception(self):
        db = Database()
        self.assertIsInstance(db, Database)

        with self.assertRaises(ValueError):
            db.bind("")

    @db_session
    def test_database_default_bind(self):
        db = Database()
        self.assertIsInstance(db, Database)

        os.environ["DATABASE_URL"] = "sqlite://:memory:"
        db.bind()
        result = db.get("SELECT 1")
        self.assertEqual(result, 1)

    @db_session
    @patch("envvars.parameters.get")
    def test_database_default_bind_from_parameters(self, mock_params):
        mock_params.return_value = "sqlite://:memory:"

        db = Database()
        self.assertIsInstance(db, Database)

        os.environ["DATABASE_URL"] = "parameters:///my-project/database_url"
        db.bind(mapping=True)
        result = db.get("SELECT 1")
        self.assertEqual(result, 1)

    @db_session
    def test_database_bind_with_mapping(self):
        db = Database()
        self.assertIsInstance(db, Database)

        class TestTable(db.Entity):
            _table_ = "test"

            id = PrimaryKey(int, auto=True)
            name = Required(str)

        db.bind("sqlite://:memory:", mapping=True)
        result = db.get("SELECT 1")
        self.assertEqual(result, 1)
