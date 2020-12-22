import json
import unittest

import api


class TestApiAuthorizer(unittest.TestCase):
    def test_instance(self):
        data = {"foo": "bar", "baz": 1}
        instance = api.Authorizer(data)

        self.assertIsInstance(instance, api.Authorizer)
        self.assertTrue(hasattr(instance, "foo"))
        self.assertTrue(hasattr(instance, "baz"))
        self.assertEqual(instance.foo, "bar")
        self.assertEqual(instance.baz, 1)
        self.assertEqual(str(instance), str(data))


class TestApiRequest(unittest.TestCase):
    def test_instance(self):
        data = {
            "requestContext": {"authorizer": {"foo": "bar", "baz": 1}},
            "body": '{"ping": "pong"}',
        }
        instance = api.Request(data)

        self.assertIsInstance(instance, api.Request)
        self.assertTrue(hasattr(instance, "authorizer"))
        self.assertTrue(hasattr(instance, "body"))
        self.assertTrue(instance.authorizer.foo, "bar")
        self.assertTrue(instance.authorizer.baz, 1)
        self.assertTrue(instance.body, {"ping": "pong"})


class TestApiHandler(unittest.TestCase):
    def test_handler(self):
        event = {
            "requestContext": {"authorizer": {"foo": "bar", "baz": 1}},
            "body": '{"ping": "pong"}',
        }
        context = {"nothing": "here"}
        expected = {
            "headers": {"Access-Control-Allow-Origin": "*"},
            "statusCode": 200,
            "body": {"foo": "bar", "ping": "pong"},
        }

        @api.handler
        def handler(request):
            res = {"foo": request.authorizer.foo, "ping": request.body["ping"]}
            return json.dumps(res)

        response = handler(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        self.assertDictEqual(json.loads(response["body"]), expected["body"])
