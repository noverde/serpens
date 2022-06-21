import os
import shlex
import unittest
from unittest.mock import Mock, call, patch

from serpens.testgres import (
    docker_init,
    docker_pg_isready,
    docker_pg_user_path,
    docker_port,
    docker_shell,
    docker_start,
    docker_stop,
    setup,
    start_test_run,
    stop_test_run,
)


class TestTestgres(unittest.TestCase):
    def setUp(self):
        run_patcher = patch("subprocess.run")
        print_patcher = patch("serpens.testgres.print")

        self.mrun = run_patcher.start()
        self.mprint = print_patcher.start()

        self.addCleanup(run_patcher.stop)
        self.addCleanup(print_patcher.stop)

    def test_docker_shell(self):
        self.mrun.return_value.stdout = "OK"
        result = docker_shell("echo OK")
        self.assertEqual(result.stdout, "OK")

    def test_docker_start(self):
        self.mrun.return_value.stdout = "OK"
        result = docker_start()
        self.assertEqual(result.stdout, "OK")

    def test_docker_stop(self):
        self.mrun.return_value.stdout = "OK"
        result = docker_stop()
        self.assertEqual(result.stdout, "OK")

    def test_docker_port(self):
        self.mrun.return_value.stdout = "foobar:65432"
        result = docker_port()
        self.assertEqual(result, "65432")

    def test_docker_port_multiline(self):
        self.mrun.return_value.stdout = "foo:65432\nbar:23456"
        result = docker_port()
        self.assertEqual(result, "65432")

    def test_docker_pg_isready(self):
        self.mrun.return_value.returncode = 2
        result = docker_pg_isready()
        self.assertEqual(result, 2)

    @patch("serpens.testgres.schema", "testgres")
    def test_docker_pg_user_path(self):
        cmd_base = "docker exec testgres psql -U testgres -d testgres -c "
        cmd_create_schema = "CREATE SCHEMA IF NOT EXISTS testgres;"
        cmd_set_user_path = "ALTER USER testgres SET search_path = testgres"

        expected_call_args = call(
            shlex.split(f"{cmd_base} '{cmd_create_schema}' -c '{cmd_set_user_path}'"),
            capture_output=True,
            encoding="utf-8",
        )

        self.mrun.return_value.returncode = 0

        result = docker_pg_user_path()

        self.assertEqual(result, 0)
        self.assertEqual(self.mrun.call_args, expected_call_args)

    @patch("serpens.testgres.schema", "test,loans")
    def test_docker_pg_user_multiple_schemas(self):
        cmd_base = "docker exec testgres psql -U testgres -d testgres -c "
        cmd_create_schema = "CREATE SCHEMA IF NOT EXISTS test; CREATE SCHEMA IF NOT EXISTS loans;"
        cmd_set_user_path = "ALTER USER testgres SET search_path = test,loans"

        expected_call_args = call(
            shlex.split(f"{cmd_base} '{cmd_create_schema}' -c '{cmd_set_user_path}'"),
            capture_output=True,
            encoding="utf-8",
        )

        self.mrun.return_value.returncode = 0

        result = docker_pg_user_path()

        self.assertEqual(result, 0)
        self.assertEqual(self.mrun.call_args, expected_call_args)

    @patch("serpens.testgres.schema", "lo~ns")
    def test_docker_pg_user_invalid_schema(self):
        self.mrun.return_value.returncode = 1
        self.mrun.return_value.stderr = "ERROR:  syntax error at or near '~'"

        result = docker_pg_user_path()

        self.assertEqual(result, 1)
        self.assertEqual(self.mrun.call_count, 1)

    def test_docker_pg_user_path_without_schema(self):
        result = docker_pg_user_path()
        self.assertIsNone(result)

    @patch("serpens.testgres.docker_pg_isready")
    def test_docker_init(self, mpgs):
        self.mrun.return_value.stdout = "foobar:65432"
        mpgs.side_effect = [1, 0]
        result = docker_init()
        self.assertEqual(result, "postgres://testgres:testgres@localhost:65432/testgres")

    @patch("serpens.testgres.docker_init")
    @patch("serpens.testgres.database")
    def test_start_test_run(self, mdb, mdi):
        expected_uri = "postgres://testgres:testgres@localhost:65432/testgres"
        mdi.return_value = expected_uri
        start_test_run(None)

        mdb.bind.assert_called_with(expected_uri, mapping=True)
        self.assertEqual(mdb.create_tables.call_count, 1)

    @patch("serpens.testgres.docker_init", Mock())
    @patch("serpens.testgres.database")
    def test_start_test_run_exception(self, mdb):
        mdb.bind.side_effect = Exception()

        start_test_run(None)

        self.assertEqual(self.mprint.call_count, 1)

    @patch("serpens.testgres.default_stop_test_run")
    def test_stop_test_run(self, mrun):
        mrun.return_value = None
        result = stop_test_run(None)
        self.assertIsNone(result)

    @patch("serpens.testgres.unittest")
    def test_setup_without_database_url(self, munit):
        db_url = None

        if "DATABASE_URL" in os.environ:
            db_url = os.environ.pop("DATABASE_URL")

        setup("")

        self.assertEqual(munit.result.TestResult.startTestRun, start_test_run)
        self.assertEqual(munit.result.TestResult.stopTestRun, stop_test_run)

        if db_url:
            os.environ["DATABASE_URL"] = db_url

    def test_setup_with_database_url(self):
        db_url = os.environ.get("DATABASE_URL")

        if not db_url:
            os.environ["DATABASE_URL"] = "postgres://testgres:testgres@localhost:55432/testgres"

        mdb = Mock()

        setup(mdb)

        self.assertEqual(mdb.create_tables.call_count, 1)

        if db_url:
            os.environ["DATABASE_URL"] = db_url
