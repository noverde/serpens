import json
from elasticapm.conf.constants import ERROR, TRANSACTION
from elasticapm.processors import for_events, MASK, varmap
from serpens.schema import SchemaEncoder


def _sanitize_var(key, value, sanitize_field_names):
    if value is None:
        return None

    if not key or isinstance(value, dict):
        return value

    key = key.lower().strip()
    for field in sanitize_field_names:
        if field.match(key):
            return MASK

    return value


@for_events(ERROR, TRANSACTION)
def sanitize_http_request_body(client, event):
    body = None

    if "context" in event and "request" in event["context"]:
        body = event["context"]["request"].get("body")

    if not isinstance(body, (dict, list)):
        return event

    body = varmap(_sanitize_var, body, sanitize_field_names=client.config.sanitize_field_names)
    event["context"]["request"]["body"] = json.dumps(body, cls=SchemaEncoder)

    return event


@for_events(ERROR, TRANSACTION)
def sanitize_http_response_body(client, event):
    if (
        "context" not in event
        or "custom" not in event["context"]
        or "response_body" not in event["context"]["custom"]
    ):
        return event

    response = event["context"]["custom"]["response_body"]

    if isinstance(response, str):
        try:
            response = json.loads(response)
        except json.JSONDecodeError:
            event["context"]["custom"].pop("response_body")
            return event

    if not isinstance(response, (dict, list)):
        event["context"]["custom"].pop("response_body")
        return event

    response = json.dumps(
        varmap(_sanitize_var, response, sanitize_field_names=client.config.sanitize_field_names),
        cls=SchemaEncoder,
    )
    event["context"]["custom"]["response_body"] = response

    return event
