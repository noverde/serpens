from elasticapm.conf.constants import ERROR, TRANSACTION
from elasticapm.processors import for_events, MASK, varmap


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


def sanitize_body(body, sanitize_fields):
    return varmap(_sanitize_var, body, sanitize_field_names=sanitize_fields)


@for_events(ERROR, TRANSACTION)
def sanitize(client, event):
    body = None

    if "context" in event and "request" in event["context"]:
        body = event["context"]["request"].get("body")

    if not isinstance(body, dict):
        return event

    event["context"]["request"]["body"] = varmap(
        _sanitize_var, body, sanitize_field_names=client.config.sanitize_field_names
    )

    return event
