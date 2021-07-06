import json
import unittest
from dataclasses import dataclass
from datetime import datetime
from copy import deepcopy

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

        @api.handler
        def handler_with_status(request):
            res = {"foo": request.authorizer.foo, "ping": request.body["ping"]}
            return 200, json.dumps(res)

        @api.handler
        def handler_with_dict(request):
            res = {
                "foo": request.authorizer.foo,
                "ping": request.body["ping"],
                "timestemp": datetime(2021, 7, 1),
            }
            return 200, res

        @api.handler
        def handler_with_list(request):
            res = [
                {
                    "foo": request.authorizer.foo,
                    "ping": request.body["ping"],
                    "timestemp": datetime(2021, 7, 1),
                }
            ]
            return 200, res

        @api.handler
        def handler_with_dataclass(request):
            @dataclass
            class FooBar:
                foo: str
                ping: str

            res = FooBar(foo=request.authorizer.foo, ping=request.body["ping"])
            return 200, res

        response = handler(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        self.assertDictEqual(json.loads(response["body"]), expected["body"])

        response = handler_with_status(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        self.assertDictEqual(json.loads(response["body"]), expected["body"])

        response = handler_with_dict(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        expected_copy = deepcopy(expected)
        expected_copy["body"]["timestemp"] = "2021-07-01T00:00:00"
        self.assertDictEqual(json.loads(response["body"]), expected_copy["body"])

        response = handler_with_list(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        expected_copy = deepcopy(expected)
        expected_copy["body"]["timestemp"] = "2021-07-01T00:00:00"

        body = json.loads(response["body"])

        self.assertIsInstance(body, list)
        self.assertIsInstance(body[0], dict)
        self.assertDictEqual(body[0], expected_copy["body"])

        response = handler_with_dataclass(event, context)

        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        self.assertDictEqual(json.loads(response["body"]), expected["body"])

    def test_handler_error(self):
        event = {
            "requestContext": {"authorizer": {"foo": "bar", "baz": 1}},
            "body": '{"ping": "pong"}',
        }
        context = {"nothing": "here"}

        @api.handler
        def handler(request):
            raise Exception()
            return {}

        response = handler(event, context)

        self.assertIn("statusCode", response)
        self.assertEqual(response["statusCode"], 500)
