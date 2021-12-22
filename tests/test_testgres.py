import unittest
from unittest.mock import patch

from serpens.testgres import (
    docker_init,
    docker_pg_isready,
    docker_port,
    docker_shell,
    docker_start,
    docker_stop,
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
    def test_docker_pg_isready(self, mrun):
        mrun.return_value.returncode = 2
        result = docker_pg_isready()
        self.assertEqual(result, 2)

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

    # @patch("serpens.testgres.docker_init", Mock())
    # @patch("serpens.testgres.database")
    # def test_start_test_run_exception(self, mdb):
    #     mdb.bind.side_effect = Exception()

    #     start_test_run(None)

    #     mdb.bind.assert_called_with(expected_uri, mapping=True)
    #     self.assertEqual(mdb.create_tables.call_count, 1)

    @patch("serpens.testgres.default_stop_test_run")
    def test_stop_test_run(self, mrun):
        mrun.return_value = None
        result = stop_test_run(None)
        self.assertIsNone(result)
