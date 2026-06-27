"""Unit tests for ``hinge.core.logging``.

Fully offline. ``configure_logging`` mutates global structlog + stdlib logging
state, so an autouse fixture snapshots/restores the third-party logger levels
and resets structlog defaults after every test. ``sys.stderr`` is redirected to
an in-memory buffer (or a fake TTY) wherever rendered output / TTY-detection is
exercised, so nothing leaks to the real console.
"""

import io
import json
import logging
import sys

import pytest
import structlog
from structlog.dev import ConsoleRenderer
from structlog.processors import JSONRenderer

from hinge.core.logging import (
    _pretty_console_renderer,
    _resolve_level,
    configure_logging,
    logger,
)

_THIRD_PARTY = ("httpx", "httpcore", "websockets")


class _FakeStderr(io.StringIO):
    """An in-memory stream with a forced ``isatty`` result."""

    def __init__(self, tty: bool):
        super().__init__()
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty


@pytest.fixture(autouse=True)
def _restore_logging_state():
    """Snapshot/restore third-party logger levels + structlog defaults."""
    saved = {name: logging.getLogger(name).level for name in _THIRD_PARTY}
    try:
        yield
    finally:
        for name, lvl in saved.items():
            logging.getLogger(name).setLevel(lvl)
        structlog.reset_defaults()


def _renderer_after_configure():
    return structlog.get_config()["processors"][-1]


# --------------------------------------------------------------------------- #
# logger
# --------------------------------------------------------------------------- #
def test_module_logger_exists():
    assert logger is not None
    assert hasattr(logger, "info")
    assert hasattr(logger, "bind")


# --------------------------------------------------------------------------- #
# _resolve_level
# --------------------------------------------------------------------------- #
def test_resolve_level_name():
    assert _resolve_level("DEBUG") == logging.DEBUG


def test_resolve_level_name_is_case_insensitive():
    assert _resolve_level("debug") == logging.DEBUG


def test_resolve_level_number_passthrough():
    assert _resolve_level(5) == 5


def test_resolve_level_unknown_name_falls_back_to_info():
    assert _resolve_level("NOT_A_LEVEL") == logging.INFO


def test_resolve_level_none_defaults_to_info(monkeypatch):
    monkeypatch.delenv("HINGE_LOG_LEVEL", raising=False)
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert _resolve_level(None) == logging.INFO


def test_resolve_level_none_reads_hinge_log_level_env(monkeypatch):
    monkeypatch.setenv("HINGE_LOG_LEVEL", "ERROR")
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    assert _resolve_level(None) == logging.ERROR


def test_resolve_level_none_reads_log_level_env(monkeypatch):
    monkeypatch.delenv("HINGE_LOG_LEVEL", raising=False)
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    assert _resolve_level(None) == logging.WARNING


def test_resolve_level_hinge_env_takes_precedence(monkeypatch):
    monkeypatch.setenv("HINGE_LOG_LEVEL", "CRITICAL")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    assert _resolve_level(None) == logging.CRITICAL


# --------------------------------------------------------------------------- #
# _pretty_console_renderer
# --------------------------------------------------------------------------- #
def test_pretty_console_renderer_returns_console_renderer():
    renderer = _pretty_console_renderer()
    assert isinstance(renderer, ConsoleRenderer)
    assert callable(renderer)


# --------------------------------------------------------------------------- #
# configure_logging — renderer selection
# --------------------------------------------------------------------------- #
def test_configure_logging_pretty_true_uses_console_renderer(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=False))
    configure_logging(level="INFO", pretty=True)
    assert structlog.is_configured()
    assert isinstance(_renderer_after_configure(), ConsoleRenderer)


def test_configure_logging_pretty_false_uses_json_renderer(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=True))
    configure_logging(level="INFO", pretty=False)
    assert structlog.is_configured()
    assert isinstance(_renderer_after_configure(), JSONRenderer)


def test_configure_logging_pretty_none_auto_tty(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=True))
    configure_logging(level="INFO", pretty=None)
    assert isinstance(_renderer_after_configure(), ConsoleRenderer)


def test_configure_logging_pretty_none_auto_not_tty(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=False))
    configure_logging(level="INFO", pretty=None)
    assert isinstance(_renderer_after_configure(), JSONRenderer)


# --------------------------------------------------------------------------- #
# configure_logging — level handling (str / int / None env)
# --------------------------------------------------------------------------- #
def test_configure_logging_level_none_uses_env(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=False))
    monkeypatch.setenv("HINGE_LOG_LEVEL", "DEBUG")
    monkeypatch.delenv("LOG_LEVEL", raising=False)
    configure_logging(level=None, pretty=False)
    assert structlog.is_configured()


@pytest.mark.parametrize("level", ["WARNING", logging.WARNING])
def test_configure_logging_filters_below_level(monkeypatch, level):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    configure_logging(level=level, pretty=False)
    log = structlog.get_logger("filter-test")
    log.info("below_threshold")
    log.warning("at_threshold")
    out = buf.getvalue()
    assert "below_threshold" not in out
    assert "at_threshold" in out


# --------------------------------------------------------------------------- #
# configure_logging — rendered output (pretty + json)
# --------------------------------------------------------------------------- #
def test_configure_logging_json_output_is_valid_json(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    configure_logging(level="INFO", pretty=False)
    structlog.get_logger("json-test").info("hello", foo="bar")
    payload = json.loads(buf.getvalue().strip())
    assert payload["event"] == "hello"
    assert payload["foo"] == "bar"


def test_configure_logging_pretty_output_contains_event(monkeypatch):
    buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buf)
    configure_logging(level="DEBUG", pretty=True)
    structlog.get_logger("pretty-test").debug("pretty_event", key="val")
    out = buf.getvalue()
    assert "pretty_event" in out


# --------------------------------------------------------------------------- #
# configure_logging — quiet_third_party
# --------------------------------------------------------------------------- #
def test_configure_logging_quiets_third_party_loggers(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=False))
    for name in _THIRD_PARTY:
        logging.getLogger(name).setLevel(logging.DEBUG)
    configure_logging(level="INFO", pretty=False, quiet_third_party=True)
    for name in _THIRD_PARTY:
        assert logging.getLogger(name).level == logging.WARNING


def test_configure_logging_leaves_third_party_when_disabled(monkeypatch):
    monkeypatch.setattr(sys, "stderr", _FakeStderr(tty=False))
    for name in _THIRD_PARTY:
        logging.getLogger(name).setLevel(logging.DEBUG)
    configure_logging(level="INFO", pretty=False, quiet_third_party=False)
    for name in _THIRD_PARTY:
        assert logging.getLogger(name).level == logging.DEBUG
