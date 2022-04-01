import os
import unittest
from pathlib import Path
from unittest.mock import patch

import envvars


class TestEnvVars(unittest.TestCase):
    path_bin = "/tmp/test.bin"

    @classmethod
    def setUpClass(cls):
        stream = open(cls.path_bin, "wb")
        stream.write(b"\x80")
        stream.close()

    @classmethod
    def tearDownClass(cls):
        os.remove(cls.path_bin)

    def unsetvar(self, envvar: str):
        if os.getenv(envvar):
            del os.environ[envvar]

    def test_load_dotenv(self):
        self.unsetvar("FOO")
        self.unsetvar("BAR")
        self.unsetvar("COMMENT")

        dotenv_file = Path(__file__).with_suffix(".env")
        envvars.load_dotenv(dotenv_file)

        self.assertEqual(os.getenv("FOO"), "BAR")
        self.assertEqual(os.getenv("BAR"), "FOO")
        self.assertIsNone(os.getenv("COMMENT"))

    def test_load_dotenv_not_found(self):
        self.unsetvar("FOO")
        envvars.load_dotenv("invalid_file.txt")
        self.assertIsNone(os.getenv("FOO"))

    def test_load_invalid_file(self):
        file = Path(self.path_bin)
        result = envvars.load_dotenv(file)

        self.assertIsNone(result)

    def test_get(self):
        os.environ["FOO"] = "BAR"
        self.assertEqual(envvars.get("FOO"), "BAR")

    def test_get_default(self):
        result = envvars.get("NOVAR", "MyValue")
        self.assertEqual(result, "MyValue")

    def test_get_default_none(self):
        result = envvars.get("NOVAR")
        self.assertIsNone(result)

    @patch("envvars.parameters.get")
    def test_get_parameter(self, mock_params):
        mock_params.return_value = "stored_value"

        os.environ["FOO"] = "parameters:///stored_parameter"
        self.assertEqual(envvars.get("FOO"), "stored_value")

    @patch("envvars.secrets_manager.get")
    def test_get_secrets(self, mock_secrets):
        mock_secrets.return_value = "stored_value"

        os.environ["FOO"] = "secrets:///stored_secret"
        self.assertEqual(envvars.get("FOO"), "stored_value")
