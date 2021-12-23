import os
import logging

import sentry_sdk

logger = logging.getLogger(__name__)


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
    )
    logger.info("Sentry's SDK initialized")
