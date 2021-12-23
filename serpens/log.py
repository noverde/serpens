import os
import logging


logger = logging.getLogger(__name__)


def setup() -> None:
    if os.getenv("LOG_LEVEL") is None:
        return

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
