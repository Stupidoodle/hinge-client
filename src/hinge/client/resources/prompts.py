"""Prompt library fetch resource."""

from typing import Any

from hinge.client.resources._base import BaseResource
from hinge.models import PromptsResponse
from hinge.prompts_manager import HingePromptsManager


class PromptsResource(BaseResource):
    """The Hinge prompt library (the question catalogue)."""

    async def fetch(self, force_refresh: bool = False) -> HingePromptsManager:
        """Fetch prompts from the API or cache."""
        if not force_refresh and self._client.prompts_manager is not None:
            return self._client.prompts_manager

        payload = await self._prompt_payload()

        response = await self._client.client.post(
            "/prompts",
            headers=self._client._get_default_headers(),
            json=payload,
        )
        response.raise_for_status()

        prompts_data = PromptsResponse.model_validate(response.json())
        self._client.prompts_manager = HingePromptsManager(prompts_data)
        self._client._save_prompts_to_cache(prompts_data)
        return self._client.prompts_manager

    async def _prompt_payload(self) -> dict[str, Any]:  # noqa: C901
        """Build the payload structure for fetching prompts."""
        preferences = await self._client.profile.preferences()
        profile = await self._client.profile.me()

        prefs_dict = preferences.model_dump(
            by_alias=True,
            exclude_none=True,
            serialize_as_any=True,
            mode="json",
        )
        selected = [str(g) for g in prefs_dict.get("genderPreferences", [])]

        def keep_selected(d: Any) -> Any:
            if isinstance(d, dict) and selected:
                return {k: v for k, v in d.items() if k in selected}
            return d

        for key in ("genderedHeightRanges", "genderedAgeRanges"):
            if key in prefs_dict:
                prefs_dict[key] = keep_selected(prefs_dict[key])

        if "dealbreakers" in prefs_dict:
            db = prefs_dict["dealbreakers"]
            for key in ("genderedHeight", "genderedAge"):
                if key in db:
                    db[key] = keep_selected(db[key])
            prefs_dict["dealbreakers"] = db

        profile_dict = profile.profile.model_dump(
            by_alias=True,
            exclude_none=True,
            serialize_as_any=True,
            mode="json",
        )

        def unwrap(obj: Any) -> Any:
            if isinstance(obj, dict) and "value" in obj and "visible" in obj:
                return unwrap(obj["value"])
            if isinstance(obj, list):
                return [unwrap(x) for x in obj]
            if isinstance(obj, dict):
                return {k: unwrap(v) for k, v in obj.items()}
            return obj

        p = unwrap(profile_dict)
        loc_name = (profile_dict.get("location") or {}).get("name")

        profile_payload = {
            "works": (
                [p.get("works")]
                if isinstance(p.get("works"), str)
                else p.get("works", [])
            ),
            "sexualOrientations": p.get("sexualOrientations", []),
            "didJustJoin": False,
            "smoking": p.get("smoking"),
            "selfieVerified": p.get("selfieVerified", False),
            "politics": p.get("politics"),
            "relationshipTypesText": p.get("relationshipTypesText", ""),
            "datingIntention": p.get("datingIntention"),
            "height": p.get("height"),
            "children": p.get("children"),
            "matchNote": p.get("matchNote", ""),
            "religions": p.get("religions", []),
            "relationshipTypes": p.get("relationshipTypeIds", []),
            "educations": p.get("educations", []),
            "age": p.get("age"),
            "jobTitle": p.get("jobTitle"),
            "birthday": p.get("birthday"),
            "drugs": p.get("drugs"),
            "content": {},
            "hometown": p.get("hometown"),
            "firstName": p.get("firstName"),
            "familyPlans": p.get("familyPlans"),
            "location": {"name": loc_name} if loc_name is not None else {"name": None},
            "marijuana": p.get("marijuana"),
            "pets": p.get("pets", []),
            "datingIntentionText": p.get("datingIntentionText", ""),
            "educationAttained": p.get("educationAttained"),
            "ethnicities": p.get("ethnicities", []),
            "pronouns": p.get("pronouns", []),
            "languagesSpoken": p.get("languagesSpoken", []),
            "lastName": p.get("lastName", ""),
            "ethnicitiesText": p.get("ethnicitiesText", ""),
            "drinking": p.get("drinking"),
            "userId": profile.user_id,
            "genderIdentityId": p.get("genderIdentityId"),
        }

        return {"preferences": prefs_dict, "profile": profile_payload}
