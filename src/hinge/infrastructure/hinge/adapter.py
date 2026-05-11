"""Hinge API adapter — maps Pydantic API models to domain models."""

import asyncio
import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from hinge.client import HingeClient
from hinge.core.logging_config import logger as log
from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage
from hinge.domain.models.like_limit import HingeLikeLimit
from hinge.domain.models.match import HingeMatch
from hinge.domain.models.profile import (
    HingeProfile,
    ProfileDateIdea,
    ProfilePhoto,
    ProfilePoll,
    ProfilePrompt,
    ProfileVideoDetail,
    ProfileVideoPrompt,
)
from hinge.domain.models.prompt import HingePrompt
from hinge.domain.models.recommendation import Recommendation
from hinge.domain.ports.hinge_api_port import HingeApiPort
from hinge.domain.ports.unit_of_work import HingeUnitOfWorkPort
from hinge.models import (
    CreateRate,
    CreateRateContent,
    CreateRateContentPrompt,
    ProfileContent,
    ProfileContentContent,
    RatePhoto,
    UserProfile,
    UserProfileV2,
)

# Rating origin mapping (internal):
# Feed origins (compatibles, active_lately, nearby, new_here) → "discover"
# Standouts feed → "standouts"
# Likes You → "likes"
# Match list → "matches"
_RATING_ORIGIN_MAP: dict[str, str] = {
    "compatibles": "discover",
    "active_lately": "discover",
    "nearby": "discover",
    "new_here": "discover",
    "standouts": "standouts",
    "likes": "likes",
    "matches": "matches",
}


def _to_rating_origin(feed_origin: str) -> str:
    """Map a feed origin to the correct rating origin."""
    return _RATING_ORIGIN_MAP.get(feed_origin, "discover")


def _unwrap_value(obj: Any) -> Any:
    """Unwrap {value, visible} wrappers into just the value."""
    if isinstance(obj, dict) and "value" in obj and "visible" in obj:
        return _unwrap_value(obj["value"])
    return obj


def _user_profile_to_domain(p: UserProfile) -> HingeProfile:
    """Convert a Pydantic UserProfile (v3) to a domain HingeProfile."""
    prof = p.profile
    return HingeProfile(
        subject_id=p.user_id,
        first_name=prof.first_name,
        age=prof.age,
        gender_id=prof.gender_id,
        height=prof.height,
        location_name=prof.location.name if prof.location else None,
        latitude=prof.location.latitude if prof.location else None,
        longitude=prof.location.longitude if prof.location else None,
        hometown=(
            prof.hometown.value if hasattr(prof.hometown, "value") else prof.hometown
        )
        if prof.hometown
        else None,
        job_title=(
            prof.job_title.value if hasattr(prof.job_title, "value") else prof.job_title
        )
        if prof.job_title
        else None,
        works=(prof.works.value if hasattr(prof.works, "value") else prof.works)
        if prof.works
        else None,
        education_attained=(
            prof.education_attained.value
            if hasattr(prof.education_attained, "value")
            else prof.education_attained
        )
        if prof.education_attained
        else None,
        selfie_verified=prof.selfie_verified or False,
        did_just_join=prof.did_just_join or False,
        last_active_status_id=prof.last_active_status_id,
        children=_unwrap_value(
            prof.children.value if hasattr(prof.children, "value") else prof.children,
        )
        if prof.children
        else None,
        dating_intention=_unwrap_value(
            prof.dating_intention.value
            if hasattr(prof.dating_intention, "value")
            else prof.dating_intention,
        )
        if prof.dating_intention
        else None,
        drinking=_unwrap_value(
            prof.drinking.value if hasattr(prof.drinking, "value") else prof.drinking,
        )
        if prof.drinking
        else None,
        drugs=_unwrap_value(
            prof.drugs.value if hasattr(prof.drugs, "value") else prof.drugs,
        )
        if prof.drugs
        else None,
        marijuana=_unwrap_value(
            prof.marijuana.value
            if hasattr(prof.marijuana, "value")
            else prof.marijuana,
        )
        if prof.marijuana
        else None,
        smoking=_unwrap_value(
            prof.smoking.value if hasattr(prof.smoking, "value") else prof.smoking,
        )
        if prof.smoking
        else None,
        politics=_unwrap_value(
            prof.politics.value if hasattr(prof.politics, "value") else prof.politics,
        )
        if prof.politics
        else None,
        family_plans=_unwrap_value(
            prof.family_plans.value
            if hasattr(prof.family_plans, "value")
            else prof.family_plans,
        )
        if prof.family_plans
        else None,
        religions=_extract_int_list(prof.religions),
        ethnicities=_extract_int_list(prof.ethnicities),
        ethnicities_text=prof.ethnicities_text or None,
        relationship_types=_extract_int_list(prof.relationship_type_ids),
        relationship_types_text=prof.relationship_types_text or None,
        languages_spoken=_extract_int_list(prof.languages_spoken),
        pets=_extract_int_list(prof.pets),
        zodiac=prof.zodiac,
        educations=_extract_educations(prof.educations),
        dating_intention_text=prof.dating_intention_text or None,
    )


def _extract_educations(val: Any) -> str | None:
    """Extract educations as a comma-joined string from wrapper or list."""
    if val is None:
        return None
    if isinstance(val, str):
        return val or None
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v) or None
    if hasattr(val, "value"):
        return _extract_educations(val.value)
    return str(val) if val else None


def _extract_works(val: Any) -> str | None:
    """Extract works as a string from various shapes (str, list, wrapper)."""
    if val is None:
        return None
    if isinstance(val, str):
        return val or None
    if isinstance(val, list):
        return ", ".join(str(v) for v in val if v) or None
    if hasattr(val, "value"):
        return _extract_works(val.value)
    return str(val) if val else None


def _extract_int_list(val: Any) -> list[int]:
    """Extract a list of ints from various Pydantic union shapes.

    Handles: list[int], list[Enum], wrapper objects with .value, None.
    """
    if val is None:
        return []
    if isinstance(val, list):
        return [
            (v.value if hasattr(v, "value") else int(v)) for v in val if v is not None
        ]
    if hasattr(val, "value"):
        inner = val.value
        if isinstance(inner, list):
            return [
                (v.value if hasattr(v, "value") else int(v))
                for v in inner
                if v is not None
            ]
        return [int(inner)] if inner is not None else []
    return []


_DEMOGRAPHIC_ATTRS = (
    "age",
    "height",
    "location_name",
    "latitude",
    "longitude",
    "hometown",
    "job_title",
    "works",
    "education_attained",
    "selfie_verified",
    "did_just_join",
    "last_active_status_id",
    "children",
    "dating_intention",
    "dating_intention_text",
    "drinking",
    "drugs",
    "marijuana",
    "smoking",
    "family_plans",
    "politics",
    "religions",
    "ethnicities",
    "ethnicities_text",
    "relationship_types",
    "relationship_types_text",
    "languages_spoken",
    "pets",
    "zodiac",
    "educations",
    "last_active_status",
)


def _copy_demographics(target: HingeProfile, source: HingeProfile) -> None:
    """Copy demographic/lifestyle fields from source onto target in-place."""
    for attr in _DEMOGRAPHIC_ATTRS:
        val = getattr(source, attr)
        if val is not None and val != [] and val != "":
            setattr(target, attr, val)


def _v2_profile_to_domain(p: UserProfileV2) -> HingeProfile:
    """Convert a v2 profile (with inline photos/answers) to domain model."""
    prof = p.profile
    return HingeProfile(
        subject_id=p.identity_id,
        first_name=prof.first_name,
        age=prof.age,
        gender_id=prof.gender_id,
        height=prof.height,
        location_name=prof.location.name if prof.location else None,
        latitude=prof.location.latitude if prof.location else None,
        longitude=prof.location.longitude if prof.location else None,
        hometown=(
            prof.hometown.value if hasattr(prof.hometown, "value") else prof.hometown
        )
        if prof.hometown
        else None,
        job_title=(
            prof.job_title.value if hasattr(prof.job_title, "value") else prof.job_title
        )
        if prof.job_title
        else None,
        works=_extract_works(prof.works),
        education_attained=(
            prof.education_attained.value
            if hasattr(prof.education_attained, "value")
            else prof.education_attained
        )
        if prof.education_attained
        else None,
        selfie_verified=prof.selfie_verified or False,
        did_just_join=prof.did_just_join or False,
        last_active_status_id=prof.last_active_status_id,
        children=_unwrap_value(
            prof.children.value if hasattr(prof.children, "value") else prof.children,
        )
        if prof.children
        else None,
        dating_intention=_unwrap_value(
            prof.dating_intention.value
            if hasattr(prof.dating_intention, "value")
            else prof.dating_intention,
        )
        if prof.dating_intention
        else None,
        drinking=_unwrap_value(
            prof.drinking.value if hasattr(prof.drinking, "value") else prof.drinking,
        )
        if prof.drinking
        else None,
        drugs=_unwrap_value(
            prof.drugs.value if hasattr(prof.drugs, "value") else prof.drugs,
        )
        if prof.drugs
        else None,
        marijuana=_unwrap_value(
            prof.marijuana.value
            if hasattr(prof.marijuana, "value")
            else prof.marijuana,
        )
        if prof.marijuana
        else None,
        smoking=_unwrap_value(
            prof.smoking.value if hasattr(prof.smoking, "value") else prof.smoking,
        )
        if prof.smoking
        else None,
        politics=_unwrap_value(
            prof.politics.value if hasattr(prof.politics, "value") else prof.politics,
        )
        if prof.politics
        else None,
        family_plans=_unwrap_value(
            prof.family_plans.value
            if hasattr(prof.family_plans, "value")
            else prof.family_plans,
        )
        if prof.family_plans
        else None,
        religions=_extract_int_list(prof.religions),
        ethnicities=_extract_int_list(prof.ethnicities),
        ethnicities_text=prof.ethnicities_text or None,
        relationship_types=_extract_int_list(prof.relationship_types),
        relationship_types_text=prof.relationship_types_text or None,
        languages_spoken=_extract_int_list(prof.languages_spoken),
        pets=_extract_int_list(prof.pets),
        zodiac=prof.zodiac,
        educations=_extract_educations(prof.educations),
        dating_intention_text=prof.dating_intention_text or None,
        last_active_status=prof.last_active_status,
    )


def _resolve_question(
    q_id: str,
    prompt_lookup: dict[str, str] | None,
) -> tuple[str, bool]:
    """Resolve question text via the prompt-id → text lookup.

    Returns ``(text, resolved)``. ``resolved`` is False when the lookup
    is present but the id is unknown — the adapter then refreshes the
    catalog and retries.
    """
    if prompt_lookup is None:
        return "", True
    text = prompt_lookup.get(q_id)
    if text is None:
        return "Unknown Question", False
    return text, True


def _answer_to_prompt(
    answer: Any,
    prompt_lookup: dict[str, str] | None,
) -> tuple[ProfilePrompt, bool]:
    """Convert an AnswerContent to a ProfilePrompt. Returns (prompt, resolved)."""
    q_id = str(answer.question_id)
    q_text, resolved = _resolve_question(q_id, prompt_lookup)
    content_type = answer.type or "text"

    audio_url = waveform = transcription = None
    if content_type == "voice":
        audio_url = answer.url
        waveform = answer.waveform
        transcription = answer.transcription

    video_url = thumbnail_url = None
    if content_type == "video":
        video_url = answer.url
        if answer.transcription_metadata:
            thumbnail_url = answer.transcription_metadata.url

    return ProfilePrompt(
        question_id=q_id,
        question_text=q_text,
        response=answer.response,
        content_type=content_type,
        content_id=answer.content_id,
        position=answer.position,
        audio_url=audio_url,
        waveform=waveform,
        transcription=transcription,
        video_url=video_url,
        thumbnail_url=thumbnail_url,
    ), resolved


def _resolve_optional_question(
    q_id: str | None,
    prompt_lookup: dict[str, str] | None,
) -> tuple[str | None, str, bool]:
    """Resolve an optional question ID. Returns (q_id_str, text, resolved)."""
    if not q_id:
        return None, "", True
    text, resolved = _resolve_question(q_id, prompt_lookup)
    return q_id, text, resolved


def _photo_to_domain(photo: Any) -> ProfilePhoto:
    """Convert a PhotoContent to a domain ProfilePhoto."""
    videos = [
        ProfileVideoDetail(
            url=v.url,
            width=v.width,
            height=v.height,
            quality=v.quality,
        )
        for v in photo.videos
    ]
    return ProfilePhoto(
        content_id=photo.content_id,
        cdn_id=photo.cdn_id,
        url=photo.url,
        width=photo.width,
        height=photo.height,
        p_hash=photo.p_hash,
        selfie_verified=photo.selfie_verified or False,
        video_url=photo.video_url,
        videos=videos,
        caption=photo.caption,
        location=photo.location,
        prompt_id=photo.prompt_id,
    )


def _reset_and_merge(
    profile: HingeProfile,
    content: ProfileContent,
    prompt_lookup: dict[str, str] | None,
) -> bool:
    """Clear transient content fields, then merge fresh content."""
    profile.photos.clear()
    profile.photo_urls.clear()
    profile.prompts.clear()
    profile.polls.clear()
    profile.video_prompt = None
    profile.date_ideas.clear()
    return _merge_content_into_profile(profile, content, prompt_lookup)


def _merge_content_into_profile(
    profile: HingeProfile,
    content: ProfileContent,
    prompt_lookup: dict[str, str] | None = None,
) -> bool:
    """Merge all content types into a domain profile.

    Returns True if all prompt question texts were resolved, False if
    any fell back to "Unknown Question" (cache may be stale).
    """
    all_resolved = True

    for photo in content.content.photos:
        profile.photos.append(_photo_to_domain(photo))
        profile.photo_urls.append(photo.url)

    for answer in content.content.answers:
        prompt, resolved = _answer_to_prompt(answer, prompt_lookup)
        profile.prompts.append(prompt)
        if not resolved:
            all_resolved = False

    if content.content.prompt_poll:
        poll = content.content.prompt_poll
        poll_q_id = str(poll.question_id)
        poll_q_text, resolved = _resolve_question(poll_q_id, prompt_lookup)
        if not resolved:
            all_resolved = False
        profile.polls.append(
            ProfilePoll(
                content_id=poll.content_id,
                question_id=poll_q_id,
                question_text=poll_q_text,
                options=poll.options,
                selected_option_index=poll.selected_option_index,
            ),
        )

    if content.content.video_prompt:
        vp = content.content.video_prompt
        q_id, q_text, resolved = _resolve_optional_question(
            str(vp.question_id) if vp.question_id else None,
            prompt_lookup,
        )
        if not resolved:
            all_resolved = False
        profile.video_prompt = ProfileVideoPrompt(
            content_id=vp.content_id,
            question_id=q_id,
            question_text=q_text,
            video_url=vp.video_url,
            thumbnail_url=vp.thumbnail_url,
            cdn_id=vp.cdn_id,
        )

    if content.content.date_idea:
        di = content.content.date_idea
        q_id, q_text, resolved = _resolve_optional_question(
            str(di.question_id) if di.question_id else None,
            prompt_lookup,
        )
        if not resolved:
            all_resolved = False
        profile.date_ideas.append(
            ProfileDateIdea(
                content_id=di.content_id,
                question_id=q_id,
                question_text=q_text,
                options=di.options,
            ),
        )

    return all_resolved


class HingeApiAdapter(HingeApiPort):
    """Adapter that implements HingeApiPort using HingeClient."""

    def __init__(
        self,
        client: HingeClient,
        uow_factory: Callable[[], HingeUnitOfWorkPort] | None = None,
    ) -> None:
        """Wrap a HingeClient and the UoW factory.

        ``uow_factory`` is required for prompts caching (DB-backed). It's
        optional so unit tests of pure mapper helpers can construct an
        adapter without standing up a DB.
        """
        self._client = client
        self._uow_factory = uow_factory
        self._prompt_lookup: dict[str, str] | None = None

    async def _ensure_prompts(
        self,
        *,
        force: bool = False,
    ) -> dict[str, str] | None:
        """Return ``{prompt_id: text}`` from DB (or API on miss / force).

        First call: try the ``hinge_prompts`` table — if populated, build
        an in-memory dict cache and return. Otherwise (or when forced)
        hit Hinge's ``/prompts`` endpoint, persist via the repo, and
        cache. Subsequent calls return the in-memory dict directly.
        """
        if not force and self._prompt_lookup is not None:
            return self._prompt_lookup

        if not force and self._uow_factory is not None:
            with self._uow_factory() as uow:
                stored = uow.prompts.list_all()
                if stored:
                    self._prompt_lookup = {p.prompt_id: p.text for p in stored}
                    return self._prompt_lookup

        try:
            response = await self._client.fetch_prompts()
        except Exception:  # noqa: BLE001 — network/auth failures are non-fatal
            return None

        prompts_domain = [
            HingePrompt(
                prompt_id=p.id,
                text=p.prompt,
                placeholder=p.placeholder,
                is_selectable=p.is_selectable,
                is_new=p.is_new,
                categories=list(p.categories),
                content_types=[str(c) for c in p.content_types],
            )
            for p in response.prompts
        ]

        if self._uow_factory is not None:
            with self._uow_factory() as uow:
                uow.prompts.bulk_upsert(prompts_domain)
                uow.commit()

        self._prompt_lookup = {p.prompt_id: p.text for p in prompts_domain}
        return self._prompt_lookup

    async def get_recommendations(self) -> list[Recommendation]:
        """Fetch recommendation feed."""
        response = await self._client.get_recommendations()
        recommendations = []
        for feed in response.feeds:
            for subject in feed.subjects:
                is_sc = False
                sc_source: int | None = None
                if subject.enhancements and subject.enhancements.second_chance:
                    is_sc = True
                    sc_source = subject.enhancements.second_chance.second_chance_source
                recommendations.append(
                    Recommendation(
                        subject_id=subject.subject_id,
                        rating_token=subject.rating_token,
                        origin=feed.origin,
                        is_second_chance=is_sc,
                        second_chance_source=sc_source,
                    ),
                )
        return recommendations

    async def get_standouts(self) -> list[Recommendation]:
        """Fetch standouts feed."""
        response = await self._client.get_standouts()
        recommendations = []
        for subject in [*response.free, *response.paid]:
            recommendations.append(
                Recommendation(
                    subject_id=subject.subject_id,
                    rating_token=subject.rating_token,
                    origin="standouts",
                ),
            )
        return recommendations

    async def get_profile_content(
        self,
        subject_ids: list[str],
    ) -> dict[str, HingeProfile]:
        """Fetch full content and build domain profiles."""
        profiles_data = await self._client.get_profiles(subject_ids)
        content_data = await self._client.get_profile_content(subject_ids)

        prompt_lookup = await self._ensure_prompts()

        result: dict[str, HingeProfile] = {}
        for p in profiles_data:
            profile = _user_profile_to_domain(p)
            result[p.user_id] = profile

        has_unknown = False
        for c in content_data:
            if c.user_id in result:
                resolved = _merge_content_into_profile(
                    result[c.user_id],
                    c,
                    prompt_lookup,
                )
                if not resolved:
                    has_unknown = True

        # Refresh cache and re-merge if any prompts were unknown
        if has_unknown and prompt_lookup:
            prompt_lookup = await self._ensure_prompts(force=True)
            if prompt_lookup:
                for c in content_data:
                    if c.user_id in result:
                        p = result[c.user_id]
                        p.prompts.clear()
                        p.polls.clear()
                        p.photos.clear()
                        p.photo_urls.clear()
                        p.video_prompt = None
                        p.date_ideas.clear()
                        _merge_content_into_profile(p, c, prompt_lookup)
                log.info("prompts_cache_refreshed_on_miss")

        return result

    async def get_profiles_quick(
        self,
        subject_ids: list[str],
        *,
        batch_size: int = 20,
    ) -> dict[str, HingeProfile]:
        """Fetch profile + basic content in batched v2 calls.

        The result dict is keyed by both ``identity_id`` (from the v2
        response) AND the original input ``subject_id`` so callers can
        look up by whichever ID format they have.
        """
        log.debug("profiles_quick_fetching", count=len(subject_ids))
        prompt_lookup = await self._ensure_prompts()

        result: dict[str, HingeProfile] = {}
        has_unknown = False
        contents: list[tuple[HingeProfile, ProfileContent]] = []

        for i in range(0, len(subject_ids), batch_size):
            chunk = subject_ids[i : i + batch_size]
            v2_data = await self._client.get_profiles_v2(chunk)
            for idx, p in enumerate(v2_data):
                profile = _v2_profile_to_domain(p)
                if p.profile.photos or p.profile.answers:
                    content = ProfileContent(
                        user_id=p.identity_id,
                        content=ProfileContentContent(
                            photos=p.profile.photos,
                            answers=p.profile.answers,
                        ),
                    )
                    resolved = _merge_content_into_profile(
                        profile,
                        content,
                        prompt_lookup,
                    )
                    if not resolved:
                        has_unknown = True
                    contents.append((profile, content))
                # Key by identity_id (from response)
                result[p.identity_id] = profile
                # Also key by original input subject_id (may differ)
                abs_idx = i + idx
                if abs_idx < len(subject_ids):
                    result[subject_ids[abs_idx]] = profile

        if has_unknown and prompt_lookup:
            await self._retry_unknown_prompts(
                [c for _, c in contents],
                {p.subject_id: p for p, _ in contents},
            )

        log.info(
            "profiles_quick_loaded",
            requested=len(subject_ids),
            returned=len(result),
        )
        return result

    async def _retry_unknown_prompts(
        self,
        all_content: list[ProfileContent],
        profile_map: dict[str, HingeProfile],
    ) -> None:
        """Re-merge content after refreshing the prompts cache."""
        prompt_lookup = await self._ensure_prompts(force=True)
        if prompt_lookup:
            for c in all_content:
                profile = profile_map.get(c.user_id)
                if profile:
                    _reset_and_merge(profile, c, prompt_lookup)
            log.info("prompts_cache_refreshed_on_miss")

    async def _retry_missing_content(
        self,
        missing_ids: list[str],
        profile_map: dict[str, HingeProfile],
        prompt_lookup: dict[str, str] | None,
        all_content: list[ProfileContent],
    ) -> bool:
        """Retry fetching content for profiles that returned nothing.

        Returns True if any content had unresolved prompts.
        """
        await asyncio.sleep(3)
        retry_data = await self._client.get_profile_content(missing_ids)
        has_unknown = False
        for c in retry_data:
            profile = profile_map.get(c.user_id)
            if profile:
                if not _reset_and_merge(profile, c, prompt_lookup):
                    has_unknown = True
                all_content.append(c)
        still_missing = len(missing_ids) - len(retry_data)
        if still_missing:
            log.info("hydrate_skipped_missing", count=still_missing)
        return has_unknown

    async def refresh_demographics(
        self,
        profiles: list[HingeProfile],
        *,
        batch_size: int = 20,
    ) -> None:
        """Re-fetch demographics from v2 API and update profiles in-place.

        This ensures DB-loaded profiles get fresh lifestyle/enum fields
        that may have been NULL when originally persisted.
        """
        if not profiles:
            return

        profile_map = {p.subject_id: p for p in profiles}
        all_ids = list(profile_map)
        updated = 0

        for i in range(0, len(all_ids), batch_size):
            chunk = all_ids[i : i + batch_size]
            v2_data = await self._client.get_profiles_v2(chunk)
            for idx, v2 in enumerate(v2_data):
                fresh = _v2_profile_to_domain(v2)
                existing = profile_map.get(v2.identity_id)
                if not existing and idx < len(chunk):
                    existing = profile_map.get(chunk[idx])
                if existing:
                    _copy_demographics(existing, fresh)
                    updated += 1

        log.info(
            "demographics_refreshed",
            total=len(profiles),
            updated=updated,
        )

    async def hydrate_profiles(
        self,
        profiles: list[HingeProfile],
        *,
        batch_size: int = 20,
    ) -> None:
        """Fetch content and merge into existing profiles in-place.

        Profiles that return no content are retried once after a short
        backoff (transient API visibility). Remaining misses are silently
        skipped — only the rejection scan should mark profiles as rejected.
        """
        if not profiles:
            return

        prompt_lookup = await self._ensure_prompts()

        profile_map = {p.subject_id: p for p in profiles}
        all_ids = list(profile_map)
        has_unknown = False
        all_content: list[ProfileContent] = []
        returned_ids: set[str] = set()

        for i in range(0, len(all_ids), batch_size):
            chunk = all_ids[i : i + batch_size]
            content_data = await self._client.get_profile_content(chunk)
            for c in content_data:
                returned_ids.add(c.user_id)
                profile = profile_map.get(c.user_id)
                if profile:
                    if not _reset_and_merge(profile, c, prompt_lookup):
                        has_unknown = True
                    all_content.append(c)

        # Retry missing profiles once after a short backoff (transient)
        missing_ids = [sid for sid in all_ids if sid not in returned_ids]
        if missing_ids:
            if await self._retry_missing_content(
                missing_ids,
                profile_map,
                prompt_lookup,
                all_content,
            ):
                has_unknown = True

        if has_unknown and prompt_lookup:
            await self._retry_unknown_prompts(all_content, profile_map)

    async def skip(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
    ) -> None:
        """Skip a recommendation."""
        payload = CreateRate(
            rating="skip",
            subject_id=subject_id,
            rating_token=rating_token,
            session_id=self._client.session_id,
            initiated_with=None,
            origin=_to_rating_origin(origin),
        )
        response = await self._client.client.post(
            "/rate/v2/initiate",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        log.info("skip_sent", subject_id=subject_id[:12], origin=origin)
        response.raise_for_status()
        self._client.remove_recommendation(subject_id)

    async def like_photo(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
        content_id: str,
        url: str,
        cdn_id: str,
        *,
        comment: str | None = None,
        superlike: bool = False,
    ) -> HingeLikeLimit:
        """Like a photo."""
        hcm_run_id = None
        if comment:
            try:
                hcm_run_id = await self._client._run_text_review(
                    comment,
                    subject_id,
                )
            except Exception:
                log.warning(
                    "text_review_failed",
                    subject_id=subject_id[:12],
                    exc_info=True,
                )
                # Proceed without HCM — some accounts don't require it
                hcm_run_id = None

        content = CreateRateContent(
            photo=RatePhoto(content_id=content_id, url=url, cdn_id=cdn_id),
            comment=comment,
        )
        payload = CreateRate(
            session_id=self._client.session_id,
            rating_token=rating_token,
            subject_id=subject_id,
            rating="note" if comment else "like",
            hcm_run_id=hcm_run_id,
            content=content,
            initiated_with="superlike" if superlike else "standard",
            origin=_to_rating_origin(origin),
        )

        response = await self._client.client.post(
            "/rate/v2/initiate",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        self._client.remove_recommendation(subject_id)
        log.info(
            "like_photo_sent",
            subject_id=subject_id[:12],
            origin=origin,
            superlike=superlike,
            has_comment=bool(comment),
        )

        data = response.json()
        limit = data.get("limit", {})
        return HingeLikeLimit(
            likes_left=limit.get("likes", limit.get("likesLeft", 0)),
            superlikes_left=limit.get("superlikes", limit.get("superlikesLeft", 0)),
        )

    async def like_prompt(
        self,
        subject_id: str,
        rating_token: str,
        origin: str,
        content_id: str,
        question: str,
        answer: str,
        *,
        comment: str | None = None,
        superlike: bool = False,
    ) -> HingeLikeLimit:
        """Like a prompt answer."""
        hcm_run_id = None
        if comment:
            try:
                hcm_run_id = await self._client._run_text_review(
                    comment,
                    subject_id,
                )
            except Exception:
                log.warning(
                    "text_review_failed",
                    subject_id=subject_id[:12],
                    exc_info=True,
                )
                hcm_run_id = None

        content = CreateRateContent(
            prompt=CreateRateContentPrompt(
                answer=answer,
                content_id=content_id,
                question=question,
            ),
            comment=comment,
        )
        payload = CreateRate(
            session_id=self._client.session_id,
            rating_token=rating_token,
            subject_id=subject_id,
            rating="note" if comment else "like",
            hcm_run_id=hcm_run_id,
            content=content,
            initiated_with="superlike" if superlike else "standard",
            origin=_to_rating_origin(origin),
        )

        response = await self._client.client.post(
            "/rate/v2/initiate",
            json=payload.model_dump(by_alias=True, exclude_none=True),
            headers=self._client._get_default_headers(),
        )
        response.raise_for_status()
        self._client.remove_recommendation(subject_id)
        log.info(
            "like_prompt_sent",
            subject_id=subject_id[:12],
            origin=origin,
            superlike=superlike,
            has_comment=bool(comment),
        )

        data = response.json()
        limit = data.get("limit", {})
        return HingeLikeLimit(
            likes_left=limit.get("likes", limit.get("likesLeft", 0)),
            superlikes_left=limit.get("superlikes", limit.get("superlikesLeft", 0)),
        )

    async def get_likes_received(self) -> list[HingeProfile]:
        """Fetch profiles who liked you."""
        await self._client.get_likes_received()
        # Structure TBD — return empty for now until response format confirmed
        return []

    async def get_matches(self) -> list[HingeMatch]:
        """Fetch match list.

        TODO: Parse GET /connection/v2 response into HingeMatch
        domain models once the response structure is mapped.
        """
        return []

    async def get_self_profile(self) -> HingeProfile:
        """Fetch own profile."""
        data = await self._client.get_self_profile()
        return _user_profile_to_domain(
            UserProfile(user_id=data.user_id, profile=data.profile),
        )

    async def update_self_profile(self, updates: dict[str, Any]) -> None:
        """Update own profile."""
        await self._client.update_self_profile(updates)

    async def get_public_profiles(
        self,
        subject_ids: list[str],
    ) -> list[HingeProfile]:
        """Fetch public profiles by IDs."""
        profiles = await self._client.get_profiles(subject_ids)
        return [_user_profile_to_domain(p) for p in profiles]

    async def get_preferences(self) -> dict[str, Any]:
        """Fetch current preferences."""
        prefs = await self._client.get_self_preferences()
        return prefs.model_dump(by_alias=True, exclude_none=True)

    async def update_preferences(self, preferences: dict[str, Any]) -> None:
        """Update preferences."""
        from hinge.models import Preferences

        prefs = Preferences.model_validate(preferences)
        await self._client.update_self_preferences(prefs)

    async def get_like_limit(self) -> HingeLikeLimit:
        """Fetch current like limits."""
        limit = await self._client.get_like_limit()
        return HingeLikeLimit(
            likes_left=limit.likes_left,
            superlikes_left=limit.super_likes_left,
            free_superlikes_left=limit.free_super_likes_left,
            free_superlike_expiration=limit.free_super_like_expiration,
        )

    async def repeat_profiles(self) -> None:
        """Recycle seen profiles."""
        await self._client.repeat_profiles()

    # --- Chat sync ---

    async def fetch_chat_state(self) -> list[HingeChatChannel]:
        """Fetch all Sendbird channels and cross-reference with connections."""
        convs_task = self._client.sendbird_get_conversations(limit=100)
        matches_task = self._client.get_matches()
        convs, matches = await asyncio.gather(convs_task, matches_task)

        connection_ids: set[str] = {
            c["subjectId"] for c in matches.get("connections", []) if c.get("subjectId")
        }
        my_id = self._client.identity_id

        channels: list[HingeChatChannel] = []
        for raw in convs.get("channels", []):
            channel = _channel_from_sendbird(raw, my_id, connection_ids)
            if channel is not None:
                channels.append(channel)
        return channels

    async def fetch_channel_messages(
        self,
        channel_url: str,
        *,
        since_ts: int = 0,
    ) -> list[HingeChatMessage]:
        """Fetch messages for a channel, optionally after a timestamp."""
        anchor = since_ts if since_ts > 0 else int(time.time() * 1000)
        data = await self._client.sendbird_get_messages(
            channel_url,
            next_limit=100,
            message_ts=anchor,
            prev_limit=0 if since_ts > 0 else 100,
        )
        my_id = self._client.identity_id
        return [
            _message_from_sendbird(raw, channel_url=channel_url, my_id=my_id)
            for raw in data.get("messages", [])
        ]


def _ms_to_dt(ms: int | None) -> datetime | None:
    """Convert a Sendbird millisecond timestamp to UTC datetime."""
    if not ms:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=UTC)


def _seconds_to_dt(seconds: int | None) -> datetime | None:
    """Convert a second-precision timestamp to UTC datetime."""
    if not seconds:
        return None
    return datetime.fromtimestamp(seconds, tz=UTC)


def _channel_from_sendbird(
    raw: dict[str, Any],
    my_id: str,
    connection_ids: set[str],
) -> HingeChatChannel | None:
    """Map a Sendbird group channel JSON object to a domain model."""
    channel_url = raw.get("channel_url")
    if not channel_url:
        return None

    counterparty = ""
    for member in raw.get("members", []):
        uid = member.get("user_id")
        if uid and uid != my_id:
            counterparty = uid
            break

    is_active = counterparty in connection_ids
    subject_id = counterparty if is_active else None

    data_str = raw.get("data") or ""
    is_match_message = False
    if data_str:
        try:
            parsed = json.loads(data_str)
            is_match_message = parsed.get("mm", 0) == 1
        except json.JSONDecodeError:
            pass

    disappearing = raw.get("disappearing_message") or {}
    sms = raw.get("sms_fallback") or {}
    inviter = raw.get("inviter") or {}
    created_by = raw.get("created_by") or {}
    last_msg = raw.get("last_message") or {}

    created_at = _seconds_to_dt(raw.get("created_at")) or datetime.now(UTC)
    now = datetime.now(UTC)

    return HingeChatChannel(
        channel_url=channel_url,
        counterparty_sendbird_id=counterparty,
        custom_type=raw.get("custom_type") or "",
        channel_created_at=created_at,
        subject_id=subject_id,
        is_connection_active=is_active,
        is_match_message=is_match_message,
        inviter_user_id=inviter.get("user_id") or None,
        created_by_user_id=created_by.get("user_id") or None,
        disappearing_message_seconds=int(
            disappearing.get("message_survival_seconds") or 0,
        ),
        disappearing_triggered_by_read=bool(
            disappearing.get("is_triggered_by_message_read"),
        ),
        sms_fallback_wait_seconds=int(sms.get("wait_seconds") or 0),
        count_preference=raw.get("count_preference") or "",
        push_trigger_option=raw.get("push_trigger_option") or "",
        has_ai_bot=bool(raw.get("has_ai_bot")),
        has_bot=bool(raw.get("has_bot")),
        is_ai_agent_channel=bool(raw.get("is_ai_agent_channel")),
        ignore_profanity_filter=bool(raw.get("ignore_profanity_filter")),
        unread_count=int(raw.get("unread_message_count") or 0),
        last_message_id=last_msg.get("message_id") if last_msg else None,
        last_message_at=_ms_to_dt(last_msg.get("created_at")) if last_msg else None,
        first_synced_at=now,
        last_synced_at=now,
        raw_json=json.dumps(raw, separators=(",", ":")),
    )


def _flatten_sorted_metaarray(items: list[dict[str, Any]]) -> dict[str, str]:
    """Flatten Sendbird sorted_metaarray [{key, value:[str]}] → {key: first_value}."""
    result: dict[str, str] = {}
    for item in items or []:
        key = item.get("key")
        value = item.get("value")
        if not key or not isinstance(value, list) or not value:
            continue
        result[key] = str(value[0])
    return result


def _message_from_sendbird(
    raw: dict[str, Any],
    *,
    channel_url: str,
    my_id: str,
) -> HingeChatMessage:
    """Map a Sendbird message JSON object to a domain model."""
    user = raw.get("user") or {}
    sender_id = user.get("user_id") or ""

    meta = _flatten_sorted_metaarray(raw.get("sorted_metaarray") or [])
    file_info = raw.get("file") or {}

    created_at = _ms_to_dt(raw.get("created_at")) or datetime.now(UTC)

    return HingeChatMessage(
        message_id=int(raw.get("message_id") or 0),
        channel_url=channel_url,
        sender_sendbird_id=sender_id,
        is_from_me=sender_id == my_id,
        message_type=raw.get("type") or "",
        body=raw.get("message") or "",
        data=raw.get("data") or "",
        custom_type=raw.get("custom_type") or "",
        created_at=created_at,
        message_survival_seconds=int(raw.get("message_survival_seconds") or 0),
        message_retention_hour=int(raw.get("message_retention_hour") or 0),
        raw_json=json.dumps(raw, separators=(",", ":")),
        updated_at=_ms_to_dt(raw.get("updated_at")),
        dedup_id=meta.get("dedup_id"),
        attempt_id=meta.get("attemptID"),
        is_match_message=meta.get("isMatchMessage") == "true",
        origin=meta.get("origin"),
        sent_from_app_version=meta.get("X-App-Version"),
        sent_from_platform=meta.get("X-Device-Platform"),
        file_url=file_info.get("url") or None,
        file_type=file_info.get("type") or None,
        file_size=(
            int(file_info["size"]) if file_info.get("size") is not None else None
        ),
        file_name=file_info.get("name") or None,
        is_removed=bool(raw.get("is_removed")),
        is_silent=bool(raw.get("silent")),
        is_op_msg=bool(raw.get("is_op_msg")),
    )
