import os
import sqlite3
import unittest

from serpens import migrations


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

    def _fetch_row(self, database_file, row_id):
        conn = sqlite3.connect(database_file)
        try:
            cursor = conn.execute("SELECT id, name FROM test WHERE id = ?", (row_id,))
            return cursor.fetchone()
        finally:
            conn.close()

    def test_migrate(self):
        migrations.migrate(f"sqlite:///{self.database_file}", self.migrations_path)

        result = self._fetch_row(self.database_file, 1)

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], "John")

    def test_migrate_handler(self):
        os.environ["DATABASE_URL"] = f"sqlite:///{self.database_file}"
        os.environ["DATABASE_MIGRATIONS_PATH"] = self.migrations_path

        migrations.migrate_handler(None, None)

        result = self._fetch_row(self.database_file, 1)

        self.assertIsNotNone(result)
        self.assertEqual(result[0], 1)
        self.assertEqual(result[1], "John")
