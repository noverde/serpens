import json
import unittest

import api


class TestApiAttrDict(unittest.TestCase):
    def test_instance(self):
        data = {"foo": "bar", "baz": 1, "pos": {"x": 0, "y": 0}}
        instance = api.AttrDict(data)

        self.assertIsInstance(instance, api.AttrDict)
        self.assertTrue(hasattr(instance, "foo"))
        self.assertTrue(hasattr(instance, "baz"))
        self.assertTrue(hasattr(instance, "pos"))
        self.assertTrue(hasattr(instance.pos, "x"))
        self.assertTrue(hasattr(instance.pos, "y"))
        self.assertTrue("foo" in instance)
        self.assertTrue("baz" in instance)
        self.assertTrue("pos" in instance)
        self.assertTrue("x" in instance.pos)
        self.assertTrue("y" in instance.pos)
        self.assertFalse("bar" in instance)
        self.assertEqual(instance.foo, "bar")
        self.assertEqual(instance.baz, 1)
        self.assertEqual(instance.pos.x, 0)
        self.assertEqual(instance.pos.y, 0)
        self.assertEqual(instance["foo"], "bar")
        self.assertEqual(instance["baz"], 1)
        self.assertEqual(instance["pos"]["x"], 0)
        self.assertEqual(instance["pos"]["y"], 0)
        self.assertEqual(str(instance), str(data))


class TestApiRequest(unittest.TestCase):
    def test_instance(self):
        data = {
            "requestContext": {
                "authorizer": {"foo": "bar", "baz": 1},
                "identity": {"sourceIp": "127.0.0.1"},
            },
            "body": '{"ping": "pong"}',
            "pathParameters": {"one": 1, "two": 2},
            "queryStringParameters": {"limit": 10, "page": 2},
            "headers": {"Accept": "*/*"},
        }
        instance = api.Request(data)

        self.assertIsInstance(instance, api.Request)
        self.assertTrue(hasattr(instance, "authorizer"))
        self.assertTrue(hasattr(instance, "body"))
        self.assertTrue(hasattr(instance, "path"))
        self.assertTrue(hasattr(instance, "query"))
        self.assertTrue(hasattr(instance, "headers"))
        self.assertTrue(hasattr(instance, "identity"))
        self.assertEqual(instance.authorizer.foo, "bar")
        self.assertEqual(instance.authorizer.baz, 1)
        self.assertEqual(instance.body, {"ping": "pong"})
        self.assertEqual(instance.path.one, 1)
        self.assertEqual(instance.path.two, 2)
        self.assertEqual(instance.query.limit, 10)
        self.assertEqual(instance.query.page, 2)
        self.assertEqual(instance.headers.Accept, "*/*")
        self.assertEqual(instance.identity.sourceIp, "127.0.0.1")


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
