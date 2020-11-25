#
# Copyright (C) 2020 Noverde Tecnologia e Pagamentos S/A
# Copyright (C) 2020 Everaldo Canuto <everaldo.canuto@gmail.com>
#
# Use of this source code is governed by an MIT-style license that can be
# found in the LICENSE file or at https://opensource.org/licenses/MIT.
#

import os
import shlex
import logging

try:
    import sentry_sdk
    _SENTRY_SDK_MISSING_DEPS = False
except ImportError as err:
    _SENTRY_SDK_MISSING_DEPS = (err.name, "sentry-sdk")

_MISSING_DEPS_ERROR = "Missing module '%s'. Try: pip install %s"

logger = logging.getLogger(__name__)


def init_env(filename=".env") -> None:
    if not os.path.isfile(filename):
        return

    try:
        stream = open(filename, "r")
        buffer = stream.readlines()
        stream.close()
    except:
        return

    for line in buffer:
        tokens = list(shlex.shlex(line, posix=True, punctuation_chars="="))
        if len(tokens) < 2:
            continue
        if tokens[0] == "export" and tokens[2] == "=":
            tokens.pop(0)

        os.environ[tokens[0]] = tokens[2] if len(tokens) > 2 else ""


def init_logger() -> None:
    logging.basicConfig(
        level=logging.getLevelName(os.getenv("LOG_LEVEL", "INFO").upper()),
        # %(asctime)s  %(name)s %(levelname)-8s %(message)s
        format="%(asctime)s %(levelname)s %(message)s"
    )
    logger.info("Logging initialized")


def init_sentry() -> None:
    if _SENTRY_SDK_MISSING_DEPS:
        raise ImportError(_MISSING_DEPS_ERROR % _SENTRY_SDK_MISSING_DEPS)

    # sentry-sdk already check for SENTRY_DSN, SENTRY_ENVIRONMENT and
    # SENTRY_RELEASE environment vars so we call check for it to keep
    # compatibility with default behavior.
    environment = os.getenv("ENVIRONMENT", "development")
    release = os.getenv("RELEASE", "my-project-name@2.3.12")
    sentry_sdk.init(
        dsn=os.getenv("SENTRY_DSN", ""),
        environment=os.getenv("SENTRY_ENVIRONMENT", environment),
        release=os.getenv("SENTRY_RELEASE", release),
        debug=os.getenv("DEBUG", "False").lower() in ("yes", "true", "t", "1")
    )
    logger.info("Sentry's SDK initialized")


def setup():
    init_env()
    init_logger()
    if not _SENTRY_SDK_MISSING_DEPS:
        init_sentry()
