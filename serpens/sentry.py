import logging
import os

logger = logging.getLogger(__name__)

try:
    import sentry_sdk
    from sentry_sdk import Hub
except ImportError:
    logger.warning("Unable to import sentry")


def logger_exception(exception: Exception) -> None:
    logger.exception(exception)

    client = Hub.current.client
    if client is not None:
        client.flush(timeout=2)


def before_send(event, hint):
    if "exc_info" in hint and isinstance(hint["exc_info"][1], FilteredEvent):
        return None

    return event


def setup() -> None:
    if "SENTRY_DSN" not in os.environ:
        return

    # sentry-sdk already check for SENTRY_DSN, SENTRY_ENVIRONMENT and
    # SENTRY_RELEASE environment vars so we call check for it to keep
    # compatibility with default behavior.
    environment = os.getenv("SENTRY_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))

    release = os.getenv("SENTRY_RELEASE", os.getenv("RELEASE", "app@0.0.0"))

    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        environment=environment,
        release=release,
        debug=os.getenv("DEBUG", "False").lower() in ("yes", "true", "1"),
        before_send=before_send,
    )
    logger.info("Sentry's SDK initialized")


class FilteredEvent(Exception):
    """
    Base class for exceptions that shouldn't be sent to Sentry
    """

    pass
