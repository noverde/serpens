from elasticapm.conf.constants import ERROR, TRANSACTION
from elasticapm.processors import for_events, BASE_SANITIZE_FIELD_NAMES, MASK, varmap


def _sanitize_var(key, value, **kwargs):
    # This function was copied from elasticapm.processors._sanitize

    if "sanitize_field_names" in kwargs:
        sanitize_field_names = kwargs["sanitize_field_names"]
    else:
        sanitize_field_names = BASE_SANITIZE_FIELD_NAMES

    if value is None:
        return

    if isinstance(value, dict):
        # varmap will call _sanitize on each k:v pair of the dict, so we don't
        # have to do anything with dicts here
        return value

    if not key:  # key can be a NoneType
        return value

    key = key.lower()
    for field in sanitize_field_names:
        if field.match(key.strip()):
            # store mask as a fixed length for security
            return MASK

    return value


@for_events(ERROR, TRANSACTION)
def sanitize(client, event):
    body = event["context"]["request"]["body"]

    if not isinstance(body, dict):
        return event

    event["context"]["request"]["body"] = varmap(
        _sanitize_var, body, sanitize_field_names=client.config.sanitize_field_names
    )

    return event
