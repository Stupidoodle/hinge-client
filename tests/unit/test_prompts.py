"""Unit tests for the prompts resource, prompt cache helpers, and catalog.

Covers:
- ``client.prompts.fetch`` (cache-hit early return, force_refresh, live fetch,
  error propagation).
- ``client.prompts._prompt_payload`` (preference filtering, dealbreaker
  filtering, ``unwrap`` recursion, works str/else branches, location name
  present/None).
- ``HingeClient`` cache helpers ``_load_prompts_from_cache`` (missing / present
  / corrupt) and ``_save_prompts_to_cache`` (success + swallowed error).
- the ``client.catalog`` property (lazy enum load + caching, prompt wiring).

Everything is offline: HTTP is mocked with respx, profile calls are mocked with
``unittest.mock.AsyncMock``, and the prompt cache lives under ``tmp_path``.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import httpx
import pytest

from hinge import Catalog, EnumCatalog, HingeClient
from hinge.models import (
    Dealbreakers,
    GenderedDealbreaker,
    GenderedRange,
    Location,
    Preferences,
    Profile,
    PromptsResponse,
    RangeDetails,
    SelfProfileResponse,
)
from hinge.models.attributes import JobTitle, Pets, Religion, Works
from hinge.prompts_manager import HingePromptsManager


def _prompts_json() -> dict:
    """A minimal but valid ``PromptsResponse`` payload (camelCase, as served)."""
    return {
        "prompts": [
            {
                "id": "p1",
                "prompt": "Two truths and a lie",
                "isSelectable": True,
                "isNew": False,
                "placeholder": "Go...",
                "categories": ["icebreakers"],
                "contentTypes": ["text"],
            }
        ],
        "categories": [
            {
                "name": "Icebreakers",
                "slug": "icebreakers",
                "isVisible": True,
                "isNew": False,
            }
        ],
    }


def _empty_manager() -> HingePromptsManager:
    """A manager wrapping an empty (but valid) prompts response."""
    return HingePromptsManager(PromptsResponse(prompts=[], categories=[]))


def _make_prefs() -> Preferences:
    """A fully-populated, validator-clean ``Preferences`` instance."""
    return Preferences(
        gendered_age_ranges=GenderedRange(
            men=RangeDetails(min=25, max=35),
            women=RangeDetails(min=24, max=36),
        ),
        gendered_height_ranges=GenderedRange(
            men=RangeDetails(min=150, max=190),
            women=RangeDetails(min=150, max=185),
        ),
        dealbreakers=Dealbreakers(
            marijuana=False,
            smoking=False,
            max_distance=False,
            drinking=False,
            education_attained=False,
            politics=False,
            relationship_types=False,
            drugs=False,
            dating_intentions=False,
            family_plans=False,
            religions=False,
            ethnicities=False,
            children=False,
            gendered_height=GenderedDealbreaker(men=True, women=False),
            gendered_age=GenderedDealbreaker(men=True, women=False),
        ),
        religions=[],
        drinking=[],
        marijuana=[],
        relationship_types=[],
        drugs=[],
        max_distance=50,
        children=[],
        ethnicities=[],
        smoking=[],
        education_attained=[],
        family_plans=[],
        dating_intentions=[],
        politics=[],
        gender_preferences=[1, 3],
    )


class _MinimalProfileInner:
    """A profile whose dump is empty (no location/works/etc.)."""

    def model_dump(self, **kwargs):
        return {}


class _MinimalMe:
    """A self-profile stand-in with an empty inner profile."""

    user_id = "min-user"

    def __init__(self):
        self.profile = _MinimalProfileInner()


def _make_me() -> SelfProfileResponse:
    """A self-profile whose attribute wrappers exercise ``unwrap`` branches."""
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return SelfProfileResponse(
        user_id="self-123",
        created=now,
        registered=now,
        modified=now,
        last_active_opt_in=True,
        paused=False,
        profile=Profile(
            first_name="Sam",
            age=30,
            location=Location(name="Paris"),
            works=Works(value="Acme Corp", visible=True),
            religions=Religion(value=[1, 2], visible=True),
            pets=Pets(value=[3], visible=True),
            job_title=JobTitle(value="Engineer", visible=True),
        ),
    )


# --- prompts.fetch ---------------------------------------------------------


async def test_fetch_cache_hit_returns_existing_manager(auth_client, respx_mock):
    """force_refresh=False + a set manager returns it without any HTTP call."""
    sentinel = _empty_manager()
    auth_client.prompts_manager = sentinel

    result = await auth_client.prompts.fetch()

    assert result is sentinel
    assert not respx_mock.calls


async def test_fetch_force_refresh_bypasses_cache(
    auth_client, respx_mock, base_url, tmp_path
):
    """force_refresh=True re-fetches even when a manager is already set."""
    auth_client.prompts_cache_file = str(tmp_path / "cache.json")
    old = _empty_manager()
    auth_client.prompts_manager = old
    auth_client.profile.preferences = AsyncMock(return_value=_make_prefs())
    auth_client.profile.me = AsyncMock(return_value=_make_me())
    route = respx_mock.post(f"{base_url}/prompts").mock(
        return_value=httpx.Response(200, json=_prompts_json()),
    )

    result = await auth_client.prompts.fetch(force_refresh=True)

    assert route.called
    assert result is not old
    assert isinstance(result, HingePromptsManager)
    assert auth_client.prompts_manager is result
    assert result.get_prompt_by_id("p1") is not None
    assert os.path.exists(auth_client.prompts_cache_file)


async def test_fetch_live_when_manager_none_sets_and_saves(
    auth_client, respx_mock, base_url, tmp_path
):
    """A None manager triggers a live fetch that wires + caches the result."""
    auth_client.prompts_cache_file = str(tmp_path / "cache.json")
    auth_client.prompts_manager = None
    auth_client.profile.preferences = AsyncMock(return_value=_make_prefs())
    auth_client.profile.me = AsyncMock(return_value=_make_me())
    route = respx_mock.post(f"{base_url}/prompts").mock(
        return_value=httpx.Response(200, json=_prompts_json()),
    )

    result = await auth_client.prompts.fetch()

    assert auth_client.prompts_manager is result
    # The posted body carries both the preferences and profile sections.
    sent = json.loads(route.calls.last.request.content)
    assert set(sent) == {"preferences", "profile"}
    assert sent["profile"]["userId"] == "self-123"
    # Cache round-trips back to the same prompt.
    cached = PromptsResponse.model_validate(
        json.loads((tmp_path / "cache.json").read_text("utf-8")),
    )
    assert cached.prompts[0].id == "p1"


async def test_fetch_raises_on_non_2xx(auth_client, respx_mock, base_url, tmp_path):
    """A non-2xx response propagates and leaves the manager/cache untouched."""
    cache_file = tmp_path / "cache.json"
    auth_client.prompts_cache_file = str(cache_file)
    auth_client.prompts_manager = None
    auth_client.profile.preferences = AsyncMock(return_value=_make_prefs())
    auth_client.profile.me = AsyncMock(return_value=_make_me())
    respx_mock.post(f"{base_url}/prompts").mock(
        return_value=httpx.Response(500, json={"error": "boom"}),
    )

    with pytest.raises(httpx.HTTPStatusError):
        await auth_client.prompts.fetch()

    assert auth_client.prompts_manager is None
    assert not cache_file.exists()


# --- prompts._prompt_payload ----------------------------------------------


async def test_prompt_payload_filters_and_unwraps(auth_client):
    """Real models: gender filtering, dealbreaker filtering, unwrap, works str."""
    auth_client.profile.preferences = AsyncMock(return_value=_make_prefs())
    auth_client.profile.me = AsyncMock(return_value=_make_me())

    payload = await auth_client.prompts._prompt_payload()

    prefs = payload["preferences"]
    # genderPreferences == [1, 3] -> only those gendered keys survive.
    assert set(prefs["genderedAgeRanges"]) == {"1"}
    assert set(prefs["genderedHeightRanges"]) == {"1"}
    assert prefs["dealbreakers"]["genderedHeight"] == {"1": False}
    assert prefs["dealbreakers"]["genderedAge"] == {"1": False}

    prof = payload["profile"]
    # works is a scalar string -> wrapped into a single-element list.
    assert prof["works"] == ["Acme Corp"]
    # value/visible wrappers are unwrapped to their plain values.
    assert prof["jobTitle"] == "Engineer"
    assert prof["religions"] == [1, 2]
    # location name present -> {"name": <name>}; userId mirrors user_id.
    assert prof["location"] == {"name": "Paris"}
    assert prof["userId"] == "self-123"


async def test_prompt_payload_empty_selection_and_missing_works(auth_client):
    """No genderPreferences -> no filtering; missing works/location name -> defaults."""

    class _FakePrefs:
        def model_dump(self, **kwargs):
            return {
                "genderedHeightRanges": {"0": {"min": 1}, "1": {"min": 2}},
                "genderedAgeRanges": {"0": {"min": 20}},
                "dealbreakers": {
                    "genderedHeight": {"0": True},
                    "genderedAge": {"1": False},
                    "smoking": True,
                },
            }

    class _FakeProfileInner:
        def model_dump(self, **kwargs):
            return {
                "location": {"name": None},
                "nested": {"value": "v", "visible": True},
                "alist": [{"value": 1, "visible": True}, "scalar", 7],
                "plain": {"a": 1},
            }

    class _FakeMe:
        user_id = "fake-user"

        def __init__(self):
            self.profile = _FakeProfileInner()

    auth_client.profile.preferences = AsyncMock(return_value=_FakePrefs())
    auth_client.profile.me = AsyncMock(return_value=_FakeMe())

    payload = await auth_client.prompts._prompt_payload()

    prefs = payload["preferences"]
    # selected is empty -> keep_selected returns dicts unchanged.
    assert prefs["genderedHeightRanges"] == {"0": {"min": 1}, "1": {"min": 2}}
    assert prefs["genderedAgeRanges"] == {"0": {"min": 20}}
    assert prefs["dealbreakers"]["genderedHeight"] == {"0": True}
    assert prefs["dealbreakers"]["genderedAge"] == {"1": False}

    prof = payload["profile"]
    # location name is None -> explicit {"name": None}; works absent -> [].
    assert prof["location"] == {"name": None}
    assert prof["works"] == []
    assert prof["userId"] == "fake-user"


async def test_prompt_payload_minimal_preferences(auth_client):
    """Absent gendered-range keys and absent dealbreakers skip those blocks."""

    class _BarePrefs:
        def model_dump(self, **kwargs):
            return {}

    auth_client.profile.preferences = AsyncMock(return_value=_BarePrefs())
    auth_client.profile.me = AsyncMock(return_value=_MinimalMe())

    payload = await auth_client.prompts._prompt_payload()

    assert payload["preferences"] == {}
    assert payload["profile"]["userId"] == "min-user"
    assert payload["profile"]["location"] == {"name": None}


async def test_prompt_payload_dealbreakers_without_gendered_keys(auth_client):
    """A dealbreakers block lacking gendered keys leaves it untouched."""

    class _DbPrefs:
        def model_dump(self, **kwargs):
            return {"dealbreakers": {"smoking": True}}

    auth_client.profile.preferences = AsyncMock(return_value=_DbPrefs())
    auth_client.profile.me = AsyncMock(return_value=_MinimalMe())

    payload = await auth_client.prompts._prompt_payload()

    assert payload["preferences"]["dealbreakers"] == {"smoking": True}


# --- cache helpers ---------------------------------------------------------


def test_load_prompts_from_cache_missing(sessions_dir, tmp_path):
    """A missing cache file yields a None manager."""
    cache = tmp_path / "nope.json"
    c = HingeClient("+15555550190", prompts_cache_file=str(cache))
    assert c.prompts_manager is None
    assert c._load_prompts_from_cache() is None


def test_load_prompts_from_cache_present(sessions_dir, tmp_path):
    """A valid cache file is loaded into a manager at construction time."""
    cache = tmp_path / "cache.json"
    cache.write_text(json.dumps(_prompts_json()), "utf-8")
    c = HingeClient("+15555550191", prompts_cache_file=str(cache))
    assert isinstance(c.prompts_manager, HingePromptsManager)
    assert c.prompts_manager.get_prompt_by_id("p1") is not None
    assert isinstance(c._load_prompts_from_cache(), HingePromptsManager)


def test_load_prompts_from_cache_corrupt_json(sessions_dir, tmp_path):
    """Unparseable JSON is swallowed into a None manager."""
    cache = tmp_path / "bad.json"
    cache.write_text("{not valid json", "utf-8")
    c = HingeClient("+15555550192", prompts_cache_file=str(cache))
    assert c.prompts_manager is None
    assert c._load_prompts_from_cache() is None


def test_load_prompts_from_cache_invalid_schema(sessions_dir, tmp_path):
    """Valid JSON that fails validation is swallowed into a None manager."""
    cache = tmp_path / "wrong.json"
    cache.write_text(json.dumps({"prompts": "not-a-list"}), "utf-8")
    c = HingeClient("+15555550193", prompts_cache_file=str(cache))
    assert c._load_prompts_from_cache() is None


def test_save_prompts_to_cache_round_trips(sessions_dir, tmp_path):
    """Saving then loading the cache preserves the prompt data."""
    cache = tmp_path / "out.json"
    c = HingeClient("+15555550194", prompts_cache_file=str(cache))
    data = PromptsResponse.model_validate(_prompts_json())

    c._save_prompts_to_cache(data)

    assert cache.exists()
    reloaded = PromptsResponse.model_validate(json.loads(cache.read_text("utf-8")))
    assert reloaded.prompts[0].id == "p1"


def test_save_prompts_to_cache_swallows_errors(sessions_dir, tmp_path):
    """An unwritable cache path is logged, not raised."""
    target = tmp_path / "a_directory"
    target.mkdir()
    c = HingeClient("+15555550195", prompts_cache_file=str(target))
    data = PromptsResponse.model_validate(_prompts_json())

    # Opening a directory for writing fails; the helper must swallow it.
    c._save_prompts_to_cache(data)

    assert target.is_dir()


# --- catalog property ------------------------------------------------------


def test_catalog_lazily_loads_and_caches_enum_catalog(client):
    """First access loads the enum catalog; later accesses reuse it."""
    client.prompts_manager = None

    cat = client.catalog

    assert isinstance(cat, Catalog)
    assert isinstance(cat.enums, EnumCatalog)
    assert cat.prompts is None

    cached = client._enum_catalog
    assert cached is not None
    cat2 = client.catalog
    assert client._enum_catalog is cached
    assert cat2.enums is cached


def test_catalog_wires_in_prompts_manager(client):
    """The catalog exposes whatever prompts manager the client holds."""
    mgr = _empty_manager()
    client.prompts_manager = mgr

    cat = client.catalog

    assert cat.prompts is mgr
