"""Rating, like responses, blocking, and like-limit resource."""

from typing import Any, Literal

from hinge.client.resources._base import BaseResource
from hinge.models import (
    AnswerContent,
    CreateRate,
    CreateRateContent,
    CreateRateContentPrompt,
    LikeLimit,
    LikeResponse,
    MatchRate,
    PhotoContent,
    RatePhoto,
    RecommendationSubject,
    RespondRate,
)


class RatingResource(BaseResource):
    """Like/superlike/note rating, responses, blocks, and like limits."""

    async def limit(self) -> LikeLimit:
        """Fetch the authenticated user's daily like and superlike limits."""
        response = await self._client.client.get(
            "/likelimit",
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return LikeLimit.model_validate(response.json())

    async def _run_text_review(self, text: str, receiver_id: str) -> str:
        """Run the pre-flight text moderation check."""
        payload = {"text": text, "receiverId": receiver_id}
        response = await self._client.client.post(
            "/flag/textreview",
            json=payload,
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()["hcmRunId"]

    async def rate(
        self,
        subject: RecommendationSubject,
        content_item: PhotoContent | AnswerContent,
        comment: str | None = None,
        use_superlike: bool = False,
    ) -> LikeResponse:
        """Rate a user with a like or superlike, optionally with a comment."""
        hcm_run_id = None
        rating_type: Literal["note", "like"] = "note" if comment else "like"

        if comment:
            hcm_run_id = await self._run_text_review(
                text=comment,
                receiver_id=subject.subject_id,
            )

        if isinstance(content_item, PhotoContent):
            rate_content = CreateRateContent(
                photo=RatePhoto(
                    content_id=content_item.content_id,
                    url=content_item.url,
                    cdn_id=content_item.cdn_id,
                ),
                comment=comment,
            )
        elif isinstance(content_item, AnswerContent):
            rate_content = CreateRateContent(
                prompt=CreateRateContentPrompt(
                    answer=content_item.response or "",
                    content_id=content_item.content_id,
                    question=self._client._resolve_prompt_text(
                        content_item.question_id
                    ),
                ),
                comment=comment,
            )
        else:
            raise TypeError("content_item must be PhotoContent or AnswerContent")

        payload = CreateRate(
            session_id=self._client.session_id,
            rating_token=subject.rating_token,
            subject_id=subject.subject_id,
            rating=rating_type,
            hcm_run_id=hcm_run_id,
            content=rate_content,
            initiated_with="superlike" if use_superlike else "standard",
        )

        response = await self._client.client.post(
            "/rate/v2/initiate",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return LikeResponse.model_validate(response.json())

    async def respond(
        self,
        subject_id: str,
        rating: Literal["like", "block"],
        *,
        sort_type: str | None = None,
    ) -> dict[str, Any]:
        """Respond to an incoming like (POST /rate/v2/respond)."""
        payload = RespondRate(
            subject_id=subject_id,
            session_id=self._client.session_id,
            rating=rating,
            sort_type=sort_type,
        )
        response = await self._client.client.post(
            "/rate/v2/respond",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()

    async def block(
        self,
        subject_id: str,
        *,
        second_chance_eligible: bool = False,
    ) -> dict[str, Any]:
        """Block/unmatch from match screen (POST /rate/v2/match)."""
        payload = MatchRate(
            subject_id=subject_id,
            session_id=self._client.session_id,
            second_chance_eligible=second_chance_eligible,
        )
        response = await self._client.client.post(
            "/rate/v2/match",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        return response.json()
