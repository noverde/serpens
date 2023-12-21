import json
import logging
from dataclasses import asdict, is_dataclass
from functools import wraps

from serpens import elastic, initializers
from serpens.schema import SchemaEncoder

initializers.setup()

logger = logging.getLogger(__name__)


def handler(func):
    @wraps(func)
    def wrapper(event, context):
        logger.debug(f"Received data: {event}")

        try:
            request = Request(event)
            result = func(request)

            if isinstance(result, Response):
                elastic.capture_response(result.body)

                return result.to_dict()

            response = Response()

            if isinstance(result, tuple) and isinstance(result[0], int):
                response.statusCode = result[0]
                result = result[1]

            if is_dataclass(result):
                result = asdict(result)

            elastic.capture_response(result)

            if isinstance(result, (dict, list)):
                result = json.dumps(result, cls=SchemaEncoder)

            response.body = result

            return response.to_dict()
        except Exception as ex:
            logger.exception(ex)
            elastic.capture_exception(ex, is_http_request=True)
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "message": str(ex),
                    }
                ),
            }

    return wrapper


class AttrDict:
    def __init__(self, data):
        for key, value in data.items():
            if type(value) is dict:
                setattr(self, key, AttrDict(value))
            else:
                setattr(self, key, value)

    def __contains__(self, name):
        return name in self.__dict__

    def __getitem__(self, name):
        return getattr(self, name)

    def __repr__(self):
        return str(self.__dict__)

    def get(self, name, default=None):
        return getattr(self, name, default)


class Request:
    def __init__(self, data):
        self.data = data
        self.authorizer = self._authorizer()
        self.body = self._body()
        self.path = self._path()
        self.query = self._query()
        self.headers = self._headers()
        self.identity = self._identity()

    def _authorizer(self):
        context = self.data.get("requestContext") or {}
        authorizer = context.get("authorizer") or {}
        return AttrDict(authorizer)

    def _body(self):
        body = self.data.get("body") or ""
        try:
            return json.loads(body)
        except json.JSONDecodeError:
            return body

    def _path(self):
        path = self.data.get("pathParameters") or {}
        return AttrDict(path)

    def _query(self):
        query = self.data.get("queryStringParameters") or {}
        return AttrDict(query)

    def _headers(self):
        headers = self.data.get("headers") or {}
        return AttrDict(headers)

    def _identity(self):
        context = self.data.get("requestContext") or {}
        identity = context.get("identity") or {}
        return AttrDict(identity)


class Response:
    def __init__(self, statusCode=200, body="", headers=None):
        self.statusCode = statusCode
        self.body = body
        self.headers = {"Access-Control-Allow-Origin": "*"}

        if headers and isinstance(headers, dict):
            self.headers.update(headers)

    def to_dict(self):
        return self.__dict__
