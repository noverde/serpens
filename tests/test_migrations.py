import os
import unittest

from pony.orm.core import db_session

from serpens import migrations
from serpens import database


class TestMigrations(unittest.TestCase):
    database_file = os.path.abspath("./tests/samples/db.sqlite3")
    migrations_path = os.path.abspath("./tests/samples/migrations")

    @classmethod
    def setUpClass(cls):
        if os.path.exists(cls.database_file):
            os.remove(cls.database_file)

    @classmethod
    def tearDownClass(cls):
        if os.path.exists(cls.database_file):
            os.remove(cls.database_file)

    @db_session
    def test_migrate(self):
        migrations.migrate(f"sqlite:///{self.database_file}", self.migrations_path)

        db = database.Database(f"sqlite://{self.database_file}")

        result = db.get("SELECT * FROM test WHERE id = 1")

        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, "John")

    @db_session
    def test_migrate_handler(self):
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_file}"
        os.environ["DATABASE_MIGRATIONS_PATH"] = self.migrations_path

        migrations.migrate_handler(None, None)

        db = database.Database(f"sqlite://{self.database_file}")
        result = db.get("SELECT * FROM test WHERE id = 1")

        self.assertIsNotNone(result)
        self.assertEqual(result.id, 1)
        self.assertEqual(result.name, "John")
