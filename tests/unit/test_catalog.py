"""Unit tests for ``hinge.core.catalog`` (EnumCatalog + Catalog).

Fully offline: the bundled ``catalog.json`` is real bundled package data, all
other inputs are synthetic dict/path sources. No network, no DB.
"""

import json
from pathlib import Path

from hinge.core.catalog import Catalog, EnumCatalog
from hinge.models import PromptsResponse
from hinge.prompts_manager import HingePromptsManager

# Synthetic catalog source. JSON-style string keys, exercising the int() coercion
# in EnumCatalog.load. Note ordinal 0 is intentionally absent from every label
# map so the special-sentinel fallback can be exercised distinctly.
SAMPLE = {
    "labels": {
        "religions": {"1": "Agnostic", "2": "Atheist", "3": "Buddhist"},
        "languages": {"10": "English", "20": "German"},
    },
    "special": {"-1": "Open to All", "0": "Prefer Not to Say", "99999999": "Unknown"},
}


def _sample_catalog() -> EnumCatalog:
    return EnumCatalog.load(dict(SAMPLE))


# --------------------------------------------------------------------------- #
# EnumCatalog.load — the three source branches + special handling             #
# --------------------------------------------------------------------------- #


def test_load_bundled_none_source():
    cat = EnumCatalog.load()
    # Bundled data has real attributes and labels.
    assert "ethnicities" in cat.attributes()
    assert cat.label("ethnicities", 1) == "Native American"
    # Bundled special sentinels are present.
    assert cat.label("ethnicities", -1) == "Open to All"


def test_load_dict_source_coerces_string_keys_to_int():
    cat = _sample_catalog()
    assert cat.attributes() == ["religions", "languages"]
    # String "1" became int 1.
    assert cat.label("religions", 1) == "Agnostic"
    assert cat.labels("religions") == {1: "Agnostic", 2: "Atheist", 3: "Buddhist"}


def test_load_path_source_as_str_and_path(tmp_path):
    p = tmp_path / "catalog.json"
    p.write_text(json.dumps(SAMPLE), "utf-8")

    from_str = EnumCatalog.load(str(p))
    assert from_str.label("languages", 10) == "English"

    from_path = EnumCatalog.load(Path(p))
    assert from_path.label("languages", 20) == "German"


def test_load_without_special_key_defaults_to_empty():
    cat = EnumCatalog.load({"labels": {"religions": {"1": "Agnostic"}}})
    # No special map -> sentinels resolve to nothing.
    assert cat.label("religions", -1) is None
    assert cat.is_valid("religions", -1) is False
    # Known ordinal still resolves normally.
    assert cat.label("religions", 1) == "Agnostic"


# --------------------------------------------------------------------------- #
# attributes / labels                                                         #
# --------------------------------------------------------------------------- #


def test_attributes_lists_all_known_attrs():
    cat = _sample_catalog()
    assert cat.attributes() == ["religions", "languages"]


def test_labels_returns_independent_copy():
    cat = _sample_catalog()
    got = cat.labels("religions")
    got[1] = "Mutated"
    # Internal state untouched by mutating the returned copy.
    assert cat.label("religions", 1) == "Agnostic"


def test_labels_unknown_attr_returns_empty_dict():
    cat = _sample_catalog()
    assert cat.labels("nope") == {}


# --------------------------------------------------------------------------- #
# label — every branch                                                        #
# --------------------------------------------------------------------------- #


def test_label_known_ordinal():
    cat = _sample_catalog()
    assert cat.label("religions", 2) == "Atheist"


def test_label_known_attr_unknown_ordinal_falls_back_to_special():
    cat = _sample_catalog()
    # 0 is absent from religions' map but present as a special sentinel.
    assert cat.label("religions", 0) == "Prefer Not to Say"


def test_label_known_attr_unknown_ordinal_not_special_is_none():
    cat = _sample_catalog()
    assert cat.label("religions", 12345) is None


def test_label_unknown_attr_falls_back_to_special():
    cat = _sample_catalog()
    # mapping is None -> straight to special lookup.
    assert cat.label("nope", -1) == "Open to All"


def test_label_unknown_attr_and_unknown_ordinal_is_none():
    cat = _sample_catalog()
    assert cat.label("nope", 555) is None


# --------------------------------------------------------------------------- #
# ordinal — case-insensitive reverse lookup                                   #
# --------------------------------------------------------------------------- #


def test_ordinal_exact_label():
    cat = _sample_catalog()
    assert cat.ordinal("religions", "Buddhist") == 3


def test_ordinal_case_insensitive():
    cat = _sample_catalog()
    assert cat.ordinal("religions", "aGnOsTiC") == 1


def test_ordinal_unknown_attr_is_none():
    cat = _sample_catalog()
    assert cat.ordinal("nope", "Agnostic") is None


def test_ordinal_unknown_label_is_none():
    cat = _sample_catalog()
    assert cat.ordinal("religions", "Pastafarian") is None


# --------------------------------------------------------------------------- #
# is_valid / set_valid_ids                                                    #
# --------------------------------------------------------------------------- #


def test_is_valid_default_includes_all_known_ordinals():
    cat = _sample_catalog()
    assert cat.is_valid("religions", 1) is True
    assert cat.is_valid("religions", 3) is True


def test_is_valid_special_ordinals_always_valid():
    cat = _sample_catalog()
    assert cat.is_valid("religions", -1) is True
    assert cat.is_valid("religions", 0) is True
    assert cat.is_valid("religions", 99999999) is True
    # Special is valid even for an attr that has no valid-id set.
    assert cat.is_valid("nope", -1) is True


def test_is_valid_unknown_ordinal_is_false():
    cat = _sample_catalog()
    assert cat.is_valid("religions", 7777) is False
    assert cat.is_valid("nope", 5) is False


def test_set_valid_ids_with_list_narrows_validity():
    cat = _sample_catalog()
    cat.set_valid_ids("religions", [1])
    assert cat.is_valid("religions", 1) is True
    # 2 and 3 were dropped from the valid set.
    assert cat.is_valid("religions", 2) is False
    assert cat.is_valid("religions", 3) is False
    # Specials remain valid regardless of the narrowed set.
    assert cat.is_valid("religions", 0) is True


def test_set_valid_ids_with_set_and_new_attr():
    cat = _sample_catalog()
    cat.set_valid_ids("languages", {99})
    assert cat.is_valid("languages", 99) is True
    assert cat.is_valid("languages", 10) is False


# --------------------------------------------------------------------------- #
# Special sentinel values via the bundled/sample special map                  #
# --------------------------------------------------------------------------- #


def test_special_value_labels():
    cat = _sample_catalog()
    assert cat.label("anything", -1) == "Open to All"
    assert cat.label("anything", 0) == "Prefer Not to Say"
    assert cat.label("anything", 99999999) == "Unknown"


# --------------------------------------------------------------------------- #
# Catalog                                                                     #
# --------------------------------------------------------------------------- #


def _empty_prompts_manager() -> HingePromptsManager:
    return HingePromptsManager(PromptsResponse(prompts=[], categories=[]))


def test_catalog_init_without_prompts_defaults_none():
    enums = _sample_catalog()
    cat = Catalog(enums)
    assert cat.enums is enums
    assert cat.prompts is None


def test_catalog_init_with_prompts():
    enums = _sample_catalog()
    pm = _empty_prompts_manager()
    cat = Catalog(enums, pm)
    assert cat.enums is enums
    assert cat.prompts is pm


def test_catalog_load_without_prompts():
    cat = Catalog.load()
    assert isinstance(cat.enums, EnumCatalog)
    # Loaded the bundled enum data.
    assert "ethnicities" in cat.enums.attributes()
    assert cat.prompts is None


def test_catalog_load_with_prompts():
    pm = _empty_prompts_manager()
    cat = Catalog.load(pm)
    assert isinstance(cat.enums, EnumCatalog)
    assert cat.prompts is pm
