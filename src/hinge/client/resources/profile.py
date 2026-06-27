"""Self-profile, preferences, photos, and public profile lookup resource."""

from typing import Any

from hinge.client.resources._base import BaseResource
from hinge.models import (
    AnswerContentPayload,
    Preferences,
    ProfileContent,
    SelfContentResponse,
    SelfProfileResponse,
    UserProfile,
    UserProfileV2,
)


class ProfileResource(BaseResource):
    """The authenticated user's profile plus public profile lookups."""

    async def me(self) -> SelfProfileResponse:
        """Fetch the authenticated user's own profile data."""
        response = await self._client.client.get(
            "/user/v3",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return SelfProfileResponse.model_validate(response.json())

    async def my_content(self) -> SelfContentResponse:
        """Fetch the authenticated user's own content."""
        response = await self._client.client.get(
            "/content/v2",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return SelfContentResponse.model_validate(response.json())

    async def state(self) -> dict[str, Any]:
        """Fetch profile completion state (GET /profilestate/profile)."""
        response = await self._client.client.get(
            "/profilestate/profile",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def basics_missing(self) -> dict[str, Any]:
        """Fetch missing profile basics (GET /profilestate/basics/missing)."""
        response = await self._client.client.get(
            "/profilestate/basics/missing",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def preferences(self) -> Preferences:
        """Fetch the authenticated user's preferences."""
        response = await self._client.client.get(
            "/preference/v2/selected",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return Preferences.model_validate(response.json())

    async def update_preferences(self, payload: Preferences) -> dict[str, Any]:
        """Update the authenticated user's preferences."""
        _payload = [payload.model_dump(by_alias=True, exclude_none=True)]
        response = await self._client.client.patch(
            "/preference/v2/selected",
            json=_payload,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def update(
        self,
        profile_updates: dict[str, Any],
    ) -> dict[str, Any]:
        """Update the authenticated user's profile."""
        payload = [{"profile": profile_updates}]
        response = await self._client.client.patch(
            "/user/v2",
            json=payload,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def update_answers(
        self,
        answers: list[AnswerContentPayload],
    ) -> dict[str, Any]:
        """Update the authenticated user's prompt answers."""
        payload = [
            answer.model_dump(by_alias=True, exclude_none=True) for answer in answers
        ]
        response = await self._client.client.put(
            "/content/v1/answers",
            json=payload,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def put_photos(
        self,
        photos: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Replace all photos (PUT /content/v1/photos).

        The upstream API is full-replacement: the ordered list you send
        becomes the new photo set. Omit a photo to delete it, reorder
        the list to reorder photos.
        """
        response = await self._client.client.put(
            "/content/v1/photos",
            json={"photos": photos},
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def cdn_token(
        self,
        tags: str = "",
        folder: str = "",
    ) -> dict[str, Any]:
        """Get a Cloudinary upload token (POST /cdn/token)."""
        response = await self._client.client.post(
            "/cdn/token",
            json={"params": {"tags": tags, "phash": "true", "folder": folder}},
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def get(self, user_ids: list[str]) -> list[UserProfile]:
        """Fetch public profile data for a list of user IDs (v3, demographics only)."""
        params = {"ids": ",".join(user_ids)}
        response = await self._client.client.get(
            "/user/v3/public",
            params=params,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return [UserProfile.model_validate(user) for user in response.json()]

    async def get_v2(self, user_ids: list[str]) -> list[UserProfileV2]:
        """Fetch profile + content in one call (v2, no pHash/waveform/poll)."""
        params = {"ids": ",".join(user_ids)}
        response = await self._client.client.get(
            "/user/v2/public",
            params=params,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return [UserProfileV2.model_validate(user) for user in response.json()]

    async def content(self, user_ids: list[str]) -> list[ProfileContent]:
        """Fetch content (photos, prompts) for a list of user IDs."""
        params = {"ids": ",".join(user_ids)}
        response = await self._client.client.get(
            "/content/v2/public",
            params=params,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        data = response.json()
        if not data:
            return []
        return [ProfileContent.model_validate(c) for c in data]

    async def traits(self) -> dict[str, Any]:
        """Fetch user traits (GET /user/v2/traits)."""
        response = await self._client.client.get(
            "/user/v2/traits",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()
