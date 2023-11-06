import json
import unittest
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from serpens import api
from unittest.mock import patch


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

    def test_get(self):
        data = {"foo": "bar"}
        instance = api.AttrDict(data)

        result = instance.get("foo")

        self.assertEqual(result, "bar")


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

    def test_invalid_json(self):
        data = {
            "requestContext": {
                "authorizer": {"foo": "bar", "baz": 1},
                "identity": {"sourceIp": "127.0.0.1"},
            },
            "pathParameters": {"one": 1, "two": 2},
            "queryStringParameters": {"limit": 10, "page": 2},
            "headers": {"Accept": "*/*"},
        }

        result = api.Request(data)

        self.assertEqual(result.body, "")


class TestApiResponse(unittest.TestCase):
    def test_instance(self):
        instance = api.Response(201, "Ok", {"Content-Type": "text/plain"})

        self.assertIsInstance(instance, api.Response)
        self.assertEqual(instance.statusCode, 201)
        self.assertEqual(instance.body, "Ok")
        self.assertDictEqual(
            instance.headers, {"Content-Type": "text/plain", "Access-Control-Allow-Origin": "*"}
        )

    def test_to_dict(self):
        expected = {"statusCode": 200, "body": "", "headers": {"Access-Control-Allow-Origin": "*"}}

        instance = api.Response()

        self.assertDictEqual(instance.to_dict(), expected)

    def test_default_header(self):
        first_response = api.Response()
        first_response.headers["Foo"] = "Bar"

        second_response = api.Response()

        self.assertDictEqual(
            first_response.headers, {"Access-Control-Allow-Origin": "*", "Foo": "Bar"}
        )
        self.assertDictEqual(second_response.headers, {"Access-Control-Allow-Origin": "*"})


class TestApiHandler(unittest.TestCase):
    def setUp(self) -> None:
        def capture_serverless(func):
            return func

        self.elastic_patcher = patch("serpens.elastic.elasticapm")
        self.mock_elastic = self.elastic_patcher.start()
        self.mock_elastic.capture_serverless = capture_serverless

        self.os_patcher = patch("serpens.elastic.os")
        self.os_mock = self.os_patcher.start()
        self.os_mock.environ = {}

    def tearDown(self) -> None:
        self.elastic_patcher.stop()
        self.os_patcher.stop()

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
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

        elastic_response = deepcopy(expected["body"])
        elastic_response["timestemp"] = datetime.fromisoformat("2021-07-01T00:00:00")

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

        @api.handler
        def handler_with_response(request):
            return api.Response(body=json.dumps(expected["body"]))

        with self.subTest(use_case=handler):
            response = handler(event, context)
            self._asserts_handler(expected, response, response["body"])

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_with_status):
            response = handler_with_status(event, context)
            self._asserts_handler(expected, response, response["body"])

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_with_dict):
            response = handler_with_dict(event, context)
            expected_copy = deepcopy(expected)
            expected_copy["body"]["timestemp"] = "2021-07-01T00:00:00"
            elastic_response = deepcopy(expected["body"])
            elastic_response["timestemp"] = datetime.fromisoformat("2021-07-01T00:00:00")
            self._asserts_handler(expected_copy, response, elastic_response)

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_with_list):
            response = handler_with_list(event, context)
            expected_copy = deepcopy(expected)
            expected_copy["body"]["timestemp"] = "2021-07-01T00:00:00"
            expected_copy["body"] = [expected_copy["body"]]
            self._asserts_handler(expected_copy, response, [elastic_response])

            body = json.loads(response["body"])
            self.assertIsInstance(body, list)
            self.assertIsInstance(body[0], dict)

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_with_dataclass):
            response = handler_with_dataclass(event, context)
            self._asserts_handler(expected, response, expected["body"])

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_with_response):
            response = handler_with_response(event, context)
            self._asserts_handler(expected, response, response["body"])

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
    def test_handler_with_elastic_setup(self):
        event = {
            "requestContext": {"authorizer": {"foo": "bar", "baz": 1}},
            "body": '{"ping": "pong"}',
        }
        context = {"nothing": "here"}
        expected = {
            "headers": {"Access-Control-Allow-Origin": "*"},
            "statusCode": 200,
            "body": {"foo": "bar", "ping": "pong", "password": 123456},
        }

        @api.handler
        def handler(request):
            res = {"foo": request.authorizer.foo, "ping": request.body["ping"], "password": 123456}
            return 200, res

        @api.handler
        def handler_json(request):
            res = {"foo": request.authorizer.foo, "ping": request.body["ping"], "password": 123456}
            return 200, json.dumps(res)

        with self.subTest(use_case=handler):
            response = handler(event, context)
            self._asserts_handler(expected, response, expected["body"])

        self.mock_elastic.reset_mock()
        with self.subTest(use_case=handler_json):
            response = handler_json(event, context)
            self._asserts_handler(expected, response, response["body"])

    @patch("serpens.elastic.ELASTIC_APM_ENABLED", True)
    @patch("serpens.elastic.ELASTIC_APM_CAPTURE_BODY", True)
    def test_handler_string(self):
        event = {
            "requestContext": {"authorizer": {"foo": "bar", "baz": 1}},
            "body": '{"ping": "pong"}',
        }

        @api.handler
        def handler_string(request):
            res = f"foo={request.authorizer.foo}&ping={request.body['ping']}&password=123456"
            return 200, json.dumps(res)

        response = handler_string(event, {})
        self.mock_elastic.set_custom_context.assert_called_once_with(
            {"response_body": response["body"]}
        )

    def _asserts_handler(self, expected, response, elastic_response):
        self.assertIn("headers", response)
        self.assertIn("statusCode", response)
        self.assertIn("body", response)
        self.assertEqual(response["headers"], expected["headers"])
        self.assertEqual(response["statusCode"], expected["statusCode"])
        self.assertEqual(json.loads(response["body"]), expected["body"])

        self.mock_elastic.set_custom_context.assert_called_once_with(
            {"response_body": elastic_response}
        )

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
