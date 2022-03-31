import unittest

from serpens import sentry


class TestSentry(unittest.TestCase):
    def test_before_send_with_exc_info(self):
        event = "foo"
        hint = {"exc_info": ["exception", "foo", "bar"]}

        response = sentry.before_send(event, hint)

        self.assertIsNotNone(response)
        self.assertEqual(response, event)

    def test_before_send_without_exc_info(self):
        event = "foo"
        hint = "bar"

        response = sentry.before_send(event, hint)

        self.assertIsNotNone(response)
        self.assertEqual(response, event)

    def test_before_send_ignore_exception(self):
        event = sentry.IgnoredException("foo")
        hint = {"exc_info": ["exception", sentry.IgnoredException("foo"), "bar"]}

        response = sentry.before_send(event, hint)

        self.assertIsNone(response)
