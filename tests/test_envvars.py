import os
import unittest
from unittest.mock import patch
from pathlib import Path

import envvars


class TestEnvVars(unittest.TestCase):
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

    def test_get(self):
        os.environ["FOO"] = "BAR"
        self.assertEqual(envvars.get("FOO"), "BAR")

    @patch("envvars.parameters.get")
    def test_get_parameter(self, mock_params):
        mock_params.return_value = "stored_value"

        os.environ["FOO"] = "parameters:///stored_parameter"
        self.assertEqual(envvars.get("FOO"), "stored_value")

    @patch("envvars.secrets.get")
    def test_get_secrets(self, mock_secrets):
        mock_secrets.return_value = "stored_value"

        os.environ["FOO"] = "secrets:///stored_secret"
        self.assertEqual(envvars.get("FOO"), "stored_value")
