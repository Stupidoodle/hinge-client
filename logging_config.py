"""Logger for the application."""

import logging
import structlog
from config import get_settings

settings = get_settings()

# Set logging level based on DEBUG setting
log_level = logging.DEBUG if settings.DEBUG else logging.INFO

logging.basicConfig(
    format="%(message)s",
    level=log_level,
)

processors = [
    structlog.stdlib.add_log_level,
    structlog.processors.CallsiteParameterAdder(
        parameters=[
            structlog.processors.CallsiteParameter.FILENAME,
            structlog.processors.CallsiteParameter.LINENO,
            structlog.processors.CallsiteParameter.FUNC_NAME,
        ]
    ),
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.dev.ConsoleRenderer(),
]

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(log_level),
    processors=processors,  # type: ignore
)


logger = structlog.get_logger()
