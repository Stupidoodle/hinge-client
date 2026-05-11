"""Shared fixtures for hinge chat tests."""

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"

MY_ID = "222222222222222222"
COUNTERPARTY_CONNECTED = "111111111111111111"
COUNTERPARTY_ORPHAN = "333333333333333333"


@pytest.fixture
def sendbird_channels() -> dict:
    return json.loads((FIXTURES / "sendbird_channels.json").read_text())


@pytest.fixture
def sendbird_messages() -> dict:
    return json.loads((FIXTURES / "sendbird_messages.json").read_text())


@pytest.fixture
def matches() -> dict:
    return json.loads((FIXTURES / "matches.json").read_text())
