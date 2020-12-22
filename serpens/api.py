import json
from dataclasses import dataclass
from functools import wraps


def handler(func):
    @wraps(func)
    def wrapper(event, context):
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

    return wrapper


@dataclass
class Authorizer:
    partner_id: int = None
    product_id: int = None
    borrower_id: int = None


class Request:
    def __init__(self, data):
        self.data = data
        self.authorizer = self._authorizer()
        self.body = self._body()

    def _authorizer(self):
        context = self.data.get("requestContext") or {}
        partner_id = context.get("authorizer").get("partner_id")
        product_id = context.get("authorizer").get("product_id")
        borrower_id = context.get("authorizer").get("borrower_id")
        Authorizer(partner_id, product_id, borrower_id)

    def _body(self):
        try:
            return json.loads(self.data)
        except json.JSONDecodeError:
            return self.data
