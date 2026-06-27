"""Unit tests for hinge.prompts_manager.HingePromptsManager.

Builds a synthetic ``PromptsResponse`` and exercises every query method,
covering both the hit and miss branch of each lookup/filter.
"""

import pytest

from hinge.enums import ContentType
from hinge.models import Prompt, PromptCategory, PromptsResponse
from hinge.prompts_manager import HingePromptsManager


@pytest.fixture
def prompts_data() -> PromptsResponse:
    """A small, branch-covering synthetic prompt catalogue."""
    prompts = [
        Prompt(
            id="p1",
            prompt="Two truths and a lie",
            is_selectable=True,
            placeholder="Share something",
            is_new=False,
            categories=["icebreakers"],
            content_types=[ContentType.TEXT],
        ),
        Prompt(
            id="p2",
            prompt="My simple pleasures",
            is_selectable=False,
            placeholder="",
            is_new=True,
            categories=["lifestyle", "icebreakers"],
            content_types=[ContentType.TEXT, ContentType.MEDIA],
        ),
        Prompt(
            id="p3",
            prompt="A life goal of mine",
            is_selectable=True,
            placeholder="Type here about goals",
            is_new=False,
            categories=["lifestyle"],
            content_types=[ContentType.MEDIA, ContentType.VOICE],
        ),
    ]
    categories = [
        PromptCategory(
            name="Icebreakers", slug="icebreakers", is_visible=True, is_new=False
        ),
        PromptCategory(
            name="Lifestyle", slug="lifestyle", is_visible=True, is_new=True
        ),
        PromptCategory(name="Hidden", slug="hidden", is_visible=False, is_new=False),
    ]
    return PromptsResponse(prompts=prompts, categories=categories)


@pytest.fixture
def manager(prompts_data: PromptsResponse) -> HingePromptsManager:
    """A manager wired to the synthetic catalogue."""
    return HingePromptsManager(prompts_data)


def test_init_builds_lookup_indexes(
    manager: HingePromptsManager, prompts_data: PromptsResponse
) -> None:
    assert manager.prompts_data is prompts_data
    assert set(manager._prompts_by_id) == {"p1", "p2", "p3"}
    assert set(manager._categories_by_slug) == {
        "icebreakers",
        "lifestyle",
        "hidden",
    }


def test_get_prompt_by_id_found(manager: HingePromptsManager) -> None:
    prompt = manager.get_prompt_by_id("p2")
    assert prompt is not None
    assert prompt.prompt == "My simple pleasures"


def test_get_prompt_by_id_missing(manager: HingePromptsManager) -> None:
    assert manager.get_prompt_by_id("does-not-exist") is None


def test_get_category_by_slug_found(manager: HingePromptsManager) -> None:
    category = manager.get_category_by_slug("lifestyle")
    assert category is not None
    assert category.name == "Lifestyle"


def test_get_category_by_slug_missing(manager: HingePromptsManager) -> None:
    assert manager.get_category_by_slug("nope") is None


def test_get_prompts_by_category_matches(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_prompts_by_category("icebreakers")}
    assert ids == {"p1", "p2"}


def test_get_prompts_by_category_empty(manager: HingePromptsManager) -> None:
    assert manager.get_prompts_by_category("unknown-category") == []


def test_get_prompts_by_content_type_text(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_prompts_by_content_type(ContentType.TEXT)}
    assert ids == {"p1", "p2"}


def test_get_prompts_by_content_type_voice(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_prompts_by_content_type(ContentType.VOICE)}
    assert ids == {"p3"}


def test_get_prompts_by_content_type_empty(manager: HingePromptsManager) -> None:
    assert manager.get_prompts_by_content_type(ContentType.POLL) == []


def test_get_selectable_prompts(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_selectable_prompts()}
    assert ids == {"p1", "p3"}


def test_get_new_prompts(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_new_prompts()}
    assert ids == {"p2"}


def test_get_text_prompts_delegates(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_text_prompts()}
    assert ids == {"p1", "p2"}


def test_get_media_prompts_delegates(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.get_media_prompts()}
    assert ids == {"p2", "p3"}


def test_search_prompts_matches_prompt_text(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.search_prompts("truths")}
    assert ids == {"p1"}


def test_search_prompts_matches_placeholder_only(
    manager: HingePromptsManager,
) -> None:
    # "goals" appears only in p3's placeholder, not in any prompt text.
    ids = {p.id for p in manager.search_prompts("goals")}
    assert ids == {"p3"}


def test_search_prompts_is_case_insensitive(manager: HingePromptsManager) -> None:
    ids = {p.id for p in manager.search_prompts("TWO")}
    assert ids == {"p1"}


def test_search_prompts_no_match(manager: HingePromptsManager) -> None:
    assert manager.search_prompts("zzz-nothing") == []


def test_get_prompt_display_text_known(manager: HingePromptsManager) -> None:
    assert manager.get_prompt_display_text("p1") == "Two truths and a lie"


def test_get_prompt_display_text_unknown(manager: HingePromptsManager) -> None:
    assert manager.get_prompt_display_text("missing") == "Unknown Question"


def test_get_visible_categories(manager: HingePromptsManager) -> None:
    slugs = {c.slug for c in manager.get_visible_categories()}
    assert slugs == {"icebreakers", "lifestyle"}


def test_export_to_json(manager: HingePromptsManager) -> None:
    exported = manager.export_to_json()
    assert isinstance(exported, dict)
    assert {"prompts", "categories"} <= exported.keys()
    assert len(exported["prompts"]) == 3
    assert len(exported["categories"]) == 3
    assert exported["prompts"][0]["id"] == "p1"
