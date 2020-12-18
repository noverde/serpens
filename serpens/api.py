from functools import wraps
from typing import Any, Callable, Dict


def handler(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(
        event: Dict[str, Any],
        context: Dict[str, Any],
        *args: Any,
        **kwargs: Any
    ) -> Dict[str, Any]:
        response = {
            "headers": {"Access-Control-Allow-Origin": "*"},
            "statusCode": 200,
            "body": "",
        }
        result = func(event, context)

        if isinstance(result, tuple) and isinstance(result[0], int):
            response["statusCode"] = result[0]
            response["body"] = result[1]
        else:
            response["body"] = result

        return response

    return wrapper
