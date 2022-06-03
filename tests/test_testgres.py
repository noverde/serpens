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
    @patch("subprocess.run")
    def test_docker_shell(self, mrun):
        mrun.return_value.stdout = "OK"
        result = docker_shell("echo OK")
        self.assertEqual(result.stdout, "OK")

    @patch("subprocess.run")
    def test_docker_start(self, mrun):
        mrun.return_value.stdout = "OK"
        result = docker_start()
        self.assertEqual(result.stdout, "OK")

    @patch("subprocess.run")
    def test_docker_stop(self, mrun):
        mrun.return_value.stdout = "OK"
        result = docker_stop()
        self.assertEqual(result.stdout, "OK")

    @patch("subprocess.run")
    def test_docker_port(self, mrun):
        mrun.return_value.stdout = "foobar:65432"
        result = docker_port()
        self.assertEqual(result, "65432")

    @patch("subprocess.run")
    def test_docker_port_multiline(self, mrun):
        mrun.return_value.stdout = "foo:65432\nbar:23456"
        result = docker_port()
        self.assertEqual(result, "65432")

    @patch("subprocess.run")
    def test_docker_pg_isready(self, mrun):
        mrun.return_value.returncode = 2
        result = docker_pg_isready()
        self.assertEqual(result, 2)

    @patch("serpens.testgres.schema", "testgres")
    @patch("subprocess.run")
    def test_docker_pg_user_path(self, mrun):
        cmd = (
            "docker exec testgres psql -U testgres -d testgres "
            "-c 'CREATE SCHEMA testgres' "
            "-c 'ALTER USER testgres SET search_path = testgres'"
        )
        expected_call_args = call(shlex.split(cmd), capture_output=True, encoding="utf-8")
        mrun.return_value.returncode = 1

        result = docker_pg_user_path()

        self.assertEqual(result, 1)
        self.assertEqual(mrun.call_args, expected_call_args)

    @patch("subprocess.run")
    def test_docker_pg_user_path_without_schema(self, mrun):
        mrun.return_value.returncode = 1
        result = docker_pg_user_path()
        self.assertIsNone(result)

    @patch("serpens.testgres.print")
    @patch("serpens.testgres.docker_pg_isready")
    @patch("subprocess.run")
    def test_docker_init(self, mrun, mpgs, mlog):
        mlog.return_value = None
        mrun.return_value.stdout = "foobar:65432"
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
    @patch("serpens.testgres.print")
    @patch("serpens.testgres.database")
    def test_start_test_run_exception(self, mdb, mpr):
        mdb.bind.side_effect = Exception()

        start_test_run(None)

        self.assertEqual(mpr.call_count, 1)

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
