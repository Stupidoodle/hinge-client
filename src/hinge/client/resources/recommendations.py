"""Recommendation feed, standouts, likes-received, and match list resource."""

from typing import Any

from hinge.client.resources._base import BaseResource
from hinge.core.logging import logger as log
from hinge.models import (
    LikesYouResponse,
    RecommendationsResponse,
    RecommendationSubject,
    StandoutsV2Response,
    StandoutsV3Response,
)


class RecommendationsResource(BaseResource):
    """Recommendation feeds, standouts, likes received, and matches."""

    async def list(self) -> RecommendationsResponse:
        """Fetch the main feed of recommended profiles."""
        payload = {
            "playerId": self._client.identity_id,
            "newHere": False,
            "activeToday": False,
        }

        response = await self._client.client.post(
            "/rec/v2",
            json=payload,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()

        recs_data = response.json()
        new_count = 0

        if "feeds" in recs_data:
            for feed in recs_data["feeds"]:
                feed_origin = feed.get("origin")
                if "subjects" in feed:
                    for subject_data in feed["subjects"]:
                        subject_data["origin"] = feed_origin
                        subject_id = subject_data.get(
                            "subjectId",
                        ) or subject_data.get("subject_id")
                        if subject_id and subject_id not in self._client._rec_cache:
                            self._client._rec_cache[subject_id] = (
                                RecommendationSubject.model_validate(subject_data)
                            )
                            new_count += 1

        # Track feed exhaustion: empty subjects = exhausted
        total_subjects = sum(
            len(f.get("subjects", [])) for f in recs_data.get("feeds", [])
        )
        self._client.feed_exhausted = total_subjects == 0

        log.info(
            "hinge_recommendations_fetched",
            new=new_count,
            exhausted=self._client.feed_exhausted,
        )
        self._client._save_recommendations()
        return RecommendationsResponse.model_validate(recs_data)

    async def repeat(self) -> dict[str, Any]:
        """Recycle previously seen profiles.

        Resets server-side "seen" flags.  Next ``rec/v2`` call returns
        recycled profiles (potentially with new rating tokens).
        """
        response = await self._client.client.get(
            "/user/repeat",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        self._client.feed_exhausted = False
        return response.json()

    async def likes_received(
        self,
        sort: str | None = None,
    ) -> LikesYouResponse:
        """Fetch profiles who liked you (GET /like/v2)."""
        params = {}
        if sort:
            params["sort"] = sort
        response = await self._client.client.get(
            "/like/v2",
            params=params or None,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return LikesYouResponse.model_validate(response.json())

    async def matches(self) -> dict[str, Any]:
        """Fetch match list (GET /connection/v2)."""
        response = await self._client.client.get(
            "/connection/v2",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def standouts(self) -> StandoutsV2Response:
        """Fetch standouts feed (GET /standouts/v2)."""
        response = await self._client.client.get(
            "/standouts/v2",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return StandoutsV2Response.model_validate(response.json())

    async def standouts_v3(self) -> StandoutsV3Response | None:
        """Fetch standouts feed (GET /standouts/v3) with ETag caching.

        Returns None if server returns 304 Not Modified (use cached data).
        """
        headers = self._client._get_default_headers()
        if self._client._standouts_etag:
            headers["If-None-Match"] = self._client._standouts_etag

        response = await self._client.client.get(
            "/standouts/v3",
            headers=headers,
        )
        if response.status_code == 304:
            return self._client._standouts_cache

        response.raise_for_status()
        etag = response.headers.get("ETag")
        if etag:
            self._client._standouts_etag = etag

        result = StandoutsV3Response.model_validate(response.json())
        self._client._standouts_cache = result
        return result

    def remove(self, subject_id: str) -> None:
        """Remove a recommendation from memory and save state."""
        if subject_id in self._client._rec_cache:
            del self._client._rec_cache[subject_id]
            self._client._save_recommendations()
