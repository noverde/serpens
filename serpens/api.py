import json
from functools import wraps
import logging

try:
    from sentry_sdk import capture_exception
    _SENTRY_SDK_MISSING_DEPS = False
except ImportError as err:
    _SENTRY_SDK_MISSING_DEPS = True


logger = logging.getLogger(__name__)


def handler(func):
    @wraps(func)
    def wrapper(event, context):
        try:
            response = {
                "headers": {"Access-Control-Allow-Origin": "*"},
                "statusCode": 200,
                "body": "",
            }
            request = Request(event)
            result = func(request)

            if isinstance(result, tuple) and isinstance(result[0], int):
                response["statusCode"] = result[0]
                response["body"] = result[1]
            else:
                response["body"] = result

            return response
        except Exception as ex:
            logger.error(str(ex))
            if not _SENTRY_SDK_MISSING_DEPS:
                capture_exception(ex)
            
            return {
                "statusCode": 500,
                "body": json.dumps({
                    "message": str(ex),
                })
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
