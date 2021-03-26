#
# Copyright (C) 2020 Noverde Tecnologia e Pagamentos S/A
# Copyright (C) 2020 Everaldo Canuto <everaldo.canuto@gmail.com>
#
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
#

import os
import logging

try:
    import sentry_sdk

    _SENTRY_SDK_MISSING_DEPS = False
except ImportError as err:
    _SENTRY_SDK_MISSING_DEPS = (err.name, "sentry-sdk")

_MISSING_DEPS_ERROR = "Missing module '%s'. Try: pip install %s"

logger = logging.getLogger(__name__)


def init_logger() -> None:
    level = logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper())

    # It seens AWS Lambda Python runtime pre-configures a logging handler, so
    # just set log level is enought.
    if logging.getLogger().hasHandlers():
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        # %(asctime)s  %(name)s %(levelname)-8s %(message)s
        format="%(asctime)s %(levelname)s %(message)s",
    )
    logger.info("Logging initialized")


def init_sentry() -> None:
    if _SENTRY_SDK_MISSING_DEPS:
        raise ImportError(_MISSING_DEPS_ERROR % _SENTRY_SDK_MISSING_DEPS)

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


def setup():
    init_logger()
    if not _SENTRY_SDK_MISSING_DEPS:
        init_sentry()
