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

    @patch("serpens.testgres.container_name", "testgres")
    @patch("serpens.testgres.testgres_port", "5433")
    @patch("serpens.testgres.testgres_network", "host")
    def test_docker_start_host_network(self):
        self.mrun.return_value.stdout = "OK"
        docker_start()
        cmd = " ".join(self.mrun.call_args[0][0])
        self.assertIn("--network host", cmd)
        self.assertIn("-e PGPORT=5433", cmd)
        self.assertNotIn("-p 5432", cmd)

    @patch("serpens.testgres.testgres_port", "5433")
    @patch("serpens.testgres.testgres_network", "host")
    def test_docker_port_host_network(self):
        self.assertEqual(docker_port(), "5433")

    def test_docker_pg_isready(self):
        self.mrun.return_value.returncode = 2
        result = docker_pg_isready()
        self.assertEqual(result, 2)

    @patch("serpens.testgres.container_name", "testgres")
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

    @patch("serpens.testgres.container_name", "testgres")
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

    @patch("serpens.testgres._wait_for_postgres_accept", return_value=True)
    @patch("serpens.testgres._wait_for_tcp", return_value=True)
    @patch("serpens.testgres.docker_pg_isready")
    def test_docker_init(self, mpgs, _mtcp, _mpg):
        self.mrun.return_value.stdout = "foobar:65432"
        mpgs.side_effect = [1, 0]
        result = docker_init()
        self.assertEqual(result, "postgresql+psycopg2://testgres:testgres@localhost:65432/testgres")

    @patch("serpens.testgres.docker_init")
    @patch("serpens.testgres.database")
    def test_start_test_run(self, mdb, mdi):
        expected_uri = "postgresql+psycopg2://testgres:testgres@localhost:65432/testgres"
        mdi.return_value = expected_uri

        mbase = Mock()
        with patch("serpens.testgres.base", mbase):
            start_test_run(None)

        mdb.bind.assert_called_with(expected_uri)
        mbase.metadata.create_all.assert_called_once()

    @patch("serpens.testgres.docker_init", Mock())
    @patch("serpens.testgres.database")
    def test_start_test_run_propagates_exception(self, mdb):
        mdb.bind.side_effect = RuntimeError("boom")
        with self.assertRaises(RuntimeError):
            start_test_run(None)

    @patch("serpens.testgres.default_stop_test_run")
    @patch("serpens.testgres.database")
    def test_stop_test_run(self, mdb, mrun):
        mrun.return_value = None
        result = stop_test_run(None)
        self.assertIsNone(result)
        mdb.dispose.assert_called_once()

    @patch("serpens.testgres.unittest")
    def test_setup_without_database_url(self, munit):
        db_url = None

        if "DATABASE_URL" in os.environ:
            db_url = os.environ.pop("DATABASE_URL")

        setup(Mock())

        self.assertEqual(munit.result.TestResult.startTestRun, start_test_run)
        self.assertEqual(munit.result.TestResult.stopTestRun, stop_test_run)

        if db_url:
            os.environ["DATABASE_URL"] = db_url

    @patch("serpens.testgres.unittest")
    def test_setup_with_database_url_defers_to_start_run(self, munit):
        db_url = os.environ.get("DATABASE_URL")
        os.environ["DATABASE_URL"] = "postgresql+psycopg2://t:t@localhost:55432/t"

        try:
            from serpens import testgres as tg

            setup(Mock())

            self.assertEqual(tg.external_uri, "postgresql+psycopg2://t:t@localhost:55432/t")
            self.assertEqual(munit.result.TestResult.startTestRun, start_test_run)
            self.assertEqual(munit.result.TestResult.stopTestRun, stop_test_run)
        finally:
            if db_url is None:
                del os.environ["DATABASE_URL"]
            else:
                os.environ["DATABASE_URL"] = db_url

    def test_setup_with_redis_mode_flags_it(self):
        from serpens import testgres as tg

        prev_db, prev_redis = os.environ.pop("DATABASE_URL", None), os.environ.pop(
            "REDIS_URL", None
        )
        try:
            setup(Mock(), redis_mode=True)
            self.assertTrue(tg.redis_enabled)
            self.assertIsNone(tg.external_redis_url)
        finally:
            tg.redis_enabled = False
            if prev_db is not None:
                os.environ["DATABASE_URL"] = prev_db
            if prev_redis is not None:
                os.environ["REDIS_URL"] = prev_redis

    @patch("serpens.testgres._wait_for_tcp", return_value=True)
    def test_docker_redis_init_returns_url(self, _mtcp):
        from serpens.testgres import docker_redis_init

        self.mrun.return_value.stdout = "6379/tcp -> 0.0.0.0:65432"
        url = docker_redis_init()
        self.assertEqual(url, "redis://localhost:65432")
