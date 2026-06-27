"""structlog logging for the Hinge client library.

The library NEVER configures global logging at import time — the host application
owns logging configuration. Internally the client logs through ``logger`` (a
structlog logger that is a no-op until something configures structlog).

For a ready-made, column-aligned, color-coded console setup (handy for CLIs,
scripts, and local development), call :func:`configure_logging`. It reproduces
the colored renderer (DIM timestamps, color-coded levels, bright-cyan event
names, magenta key-values, rich tracebacks) but only when you ask for it.
"""

import logging
import os
import sys
from typing import Any

import structlog

__all__ = ["logger", "configure_logging"]

# Module logger used throughout the client. Import-safe: this does not configure
# structlog, so importing the library does not touch the host app's logging.
logger: Any = structlog.get_logger("hinge")

_THIRD_PARTY_NOISE = ("httpx", "httpcore", "websockets")


def _pretty_console_renderer() -> Any:
    """Build the colored, column-aligned console renderer."""
    from structlog.dev import (
        BRIGHT,
        CYAN,
        DIM,
        GREEN,
        MAGENTA,
        RED,
        RESET_ALL,
        YELLOW,
        Column,
        ConsoleRenderer,
        KeyValueColumnFormatter,
        LogLevelColumnFormatter,
        RichTracebackFormatter,
    )

    return ConsoleRenderer(
        sort_keys=False,
        exception_formatter=RichTracebackFormatter(
            show_locals=False,
            max_frames=20,
            width=120,
            indent_guides=True,
        ),
        columns=[
            Column(
                "timestamp",
                KeyValueColumnFormatter(
                    key_style=None,
                    value_style=DIM,
                    reset_style=RESET_ALL,
                    value_repr=str,
                    width=9,
                ),
            ),
            Column(
                "level",
                LogLevelColumnFormatter(
                    level_styles={
                        "critical": RED + BRIGHT,
                        "exception": RED + BRIGHT,
                        "error": RED,
                        "warning": YELLOW,
                        "info": GREEN,
                        "debug": DIM,
                        "notset": "",
                    },
                    reset_style=RESET_ALL,
                    width=9,
                ),
            ),
            Column(
                "event",
                KeyValueColumnFormatter(
                    key_style=None,
                    value_style=BRIGHT + CYAN,
                    reset_style=RESET_ALL,
                    value_repr=str,
                    width=45,
                ),
            ),
            Column(
                "",
                KeyValueColumnFormatter(
                    key_style=DIM,
                    value_style=MAGENTA,
                    reset_style=RESET_ALL,
                    value_repr=repr,
                ),
            ),
        ],
    )


def _resolve_level(level: str | int | None) -> int:
    """Resolve a level name/number, falling back to env then INFO."""
    if level is None:
        level = os.environ.get("HINGE_LOG_LEVEL") or os.environ.get("LOG_LEVEL") or "INFO"
    if isinstance(level, str):
        return logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    return level


def configure_logging(
    level: str | int | None = None,
    *,
    pretty: bool | None = None,
    quiet_third_party: bool = True,
) -> None:
    """Configure structlog for an application (opt-in; never called on import).

    Args:
        level: Level name (e.g. ``"DEBUG"``) or number. Defaults to the
            ``HINGE_LOG_LEVEL`` / ``LOG_LEVEL`` env var, else ``"INFO"``.
        pretty: Force the colored column console renderer (``True``) or JSON
            (``False``). Defaults to auto — pretty when stderr is a TTY, else JSON.
        quiet_third_party: Raise httpx/httpcore/websockets loggers to WARNING.
    """
    resolved = _resolve_level(level)

    if pretty is None:
        pretty = sys.stderr.isatty()

    if quiet_third_party:
        for name in _THIRD_PARTY_NOISE:
            logging.getLogger(name).setLevel(logging.WARNING)

    logging.basicConfig(format="%(message)s", level=resolved, stream=sys.stderr)

    renderer: Any = (
        _pretty_console_renderer() if pretty else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        wrapper_class=structlog.make_filtering_bound_logger(resolved),
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S" if pretty else "iso"),
            renderer,
        ],
    )
