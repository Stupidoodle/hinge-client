"""Hinge recommendation feed + voting endpoints."""

import asyncio
import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.api.schemas import (
    ContentItemOut,
    DateIdeaOut,
    HingeEncounterOut,
    HingeLikeRequest,
    HingeLikeResponse,
    HingeRecommendationsResponse,
    PhotoDetailOut,
    PollOut,
    PromptOut,
    VideoDetailOut,
    VideoPromptOut,
)
from hinge.bootstrap import HingeContainer
from hinge.domain import enums
from hinge.domain.models.decision import HingeDecision
from hinge.domain.models.profile import HingeProfile
from hinge.infrastructure.hinge.adapter import _copy_demographics

router = APIRouter(prefix="/recommendations", tags=["hinge-recommendations"])

_EARTH_RADIUS_KM = 6371.0


def _haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Haversine distance between two (lat, lon) points in km."""
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return _EARTH_RADIUS_KM * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _profile_to_encounter(
    profile: HingeProfile,
    rating_token: str,
    origin: str,
    *,
    score: float | None = None,
    reasoning: str | None = None,
    is_standout: bool = False,
    is_second_chance: bool = False,
    second_chance_source: int | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
) -> HingeEncounterOut:
    """Convert a domain profile to an encounter card.

    Builds all 5 content types (photo, text prompt, voice, video,
    poll) into ``content_items`` for interleaved rendering.
    """
    photo_details = [
        PhotoDetailOut(
            content_id=p.content_id,
            cdn_id=p.cdn_id,
            url=p.url,
            p_hash=p.p_hash,
            caption=p.caption,
            location=p.location,
            prompt_id=p.prompt_id,
            video_url=p.video_url,
            videos=[
                VideoDetailOut(
                    url=v.url,
                    width=v.width,
                    height=v.height,
                    quality=v.quality,
                )
                for v in p.videos
            ],
        )
        for p in profile.photos
    ]
    prompts = [
        PromptOut(
            content_id=p.content_id,
            question_id=p.question_id,
            question_text=p.question_text,
            response=p.response,
            content_type=p.content_type,
            position=p.position,
            audio_url=p.audio_url,
            waveform=p.waveform,
            transcription=p.transcription,
            video_url=p.video_url,
            thumbnail_url=p.thumbnail_url,
        )
        for p in profile.prompts
    ]
    polls = [
        PollOut(
            content_id=pl.content_id,
            question_id=pl.question_id,
            question_text=pl.question_text,
            options=pl.options,
            selected_option_index=pl.selected_option_index,
        )
        for pl in profile.polls
    ]

    # Build interleaved content_items for display ordering
    content_items: list[ContentItemOut] = []
    for p in profile.photos:
        is_video = bool(p.video_url or p.videos)
        content_items.append(
            ContentItemOut(
                content_id=p.content_id,
                type="video" if is_video else "photo",
                url=p.url,
                cdn_id=p.cdn_id,
                caption=p.caption,
                photo_location=p.location,
                prompt_id=p.prompt_id,
                video_url=p.video_url or (p.videos[0].url if p.videos else None),
                thumbnail_url=p.url if is_video else None,
            ),
        )
    for p in profile.prompts:
        ct = p.content_type or "text"
        item = ContentItemOut(
            content_id=p.content_id or p.question_id,
            type=ct if ct != "text" else "prompt",
            position=p.position,
            question=p.question_text,
            answer=p.response,
            audio_url=p.audio_url,
            waveform=p.waveform,
            transcription=p.transcription,
            video_url=p.video_url,
            thumbnail_url=p.thumbnail_url,
        )
        content_items.append(item)
    for pl in profile.polls:
        content_items.append(
            ContentItemOut(
                content_id=pl.content_id,
                type="poll",
                question=pl.question_text,
                options=pl.options,
                selected_option_index=pl.selected_option_index,
            ),
        )
    if profile.video_prompt:
        vp = profile.video_prompt
        content_items.append(
            ContentItemOut(
                content_id=vp.content_id,
                type="video_prompt",
                question=vp.question_text,
                video_url=vp.video_url,
                thumbnail_url=vp.thumbnail_url,
                cdn_id=vp.cdn_id,
            ),
        )
    for di in profile.date_ideas:
        content_items.append(
            ContentItemOut(
                content_id=di.content_id,
                type="date_idea",
                question=di.question_text,
                options=di.options,
            ),
        )

    # Build standalone output objects
    video_prompt_out = None
    if profile.video_prompt:
        vp = profile.video_prompt
        video_prompt_out = VideoPromptOut(
            content_id=vp.content_id,
            question_id=vp.question_id,
            question_text=vp.question_text,
            video_url=vp.video_url,
            thumbnail_url=vp.thumbnail_url,
            cdn_id=vp.cdn_id,
        )
    date_ideas_out = [
        DateIdeaOut(
            content_id=di.content_id,
            question_id=di.question_id,
            question_text=di.question_text,
            options=di.options,
        )
        for di in profile.date_ideas
    ]

    # Compute distance if both user and profile coords available
    distance_km: float | None = None
    if (
        user_lat is not None
        and user_lon is not None
        and profile.latitude is not None
        and profile.longitude is not None
    ):
        distance_km = round(
            _haversine_km(user_lat, user_lon, profile.latitude, profile.longitude),
            1,
        )

    return HingeEncounterOut(
        subject_id=profile.subject_id,
        first_name=profile.first_name,
        age=profile.age,
        photos=profile.photo_urls,
        photo_details=photo_details,
        prompts=prompts,
        polls=polls,
        location=profile.location_name,
        distance_km=distance_km,
        job_title=profile.job_title,
        height=profile.height,
        selfie_verified=profile.selfie_verified,
        did_just_join=profile.did_just_join,
        last_active_status_id=profile.last_active_status_id,
        # Lifestyle — resolve enum IDs to display labels
        hometown=profile.hometown,
        works=profile.works,
        education_attained=enums.resolve(
            enums.EDUCATION_ATTAINED,
            profile.education_attained,
        ),
        children=enums.resolve(enums.CHILDREN, profile.children),
        dating_intention=enums.resolve(
            enums.DATING_INTENTIONS,
            profile.dating_intention,
        ),
        dating_intention_text=profile.dating_intention_text,
        family_plans=enums.resolve(
            enums.FAMILY_PLANS,
            profile.family_plans,
        ),
        relationship_types=enums.resolve_list(
            enums.RELATIONSHIP_TYPES,
            profile.relationship_types,
        ),
        relationship_types_text=profile.relationship_types_text,
        drinking=enums.resolve(enums.VICES, profile.drinking),
        smoking=enums.resolve(enums.VICES, profile.smoking),
        drugs=enums.resolve(enums.VICES, profile.drugs),
        marijuana=enums.resolve(enums.VICES, profile.marijuana),
        religions=enums.resolve_list(enums.RELIGIONS, profile.religions),
        politics=enums.resolve(enums.POLITICS, profile.politics),
        ethnicities=enums.resolve_list(enums.ETHNICITIES, profile.ethnicities),
        ethnicities_text=profile.ethnicities_text,
        languages_spoken=enums.resolve_list(enums.LANGUAGES, profile.languages_spoken),
        pets=enums.resolve_list(enums.PETS, profile.pets),
        zodiac=enums.resolve(enums.ZODIAC, profile.zodiac),
        educations=profile.educations,
        last_active_status=profile.last_active_status,
        # Scoring & context
        score=score,
        reasoning=reasoning,
        rating_token=rating_token,
        origin=origin,
        content_items=content_items,
        video_prompt=video_prompt_out,
        date_ideas=date_ideas_out,
        is_standout=is_standout,
        is_second_chance=is_second_chance,
        second_chance_source=second_chance_source,
    )


async def _fetch_and_persist(container: HingeContainer) -> int:
    """Fetch upstream recommendations, hydrate, and persist new profiles."""
    recs = await container.hinge_api.get_recommendations()
    if not recs:
        log.debug("fetch_persist_empty")
        return 0

    subject_ids = [r.subject_id for r in recs]
    profiles_map = await container.hinge_api.get_profile_content(
        subject_ids,
    )

    new_count = 0
    updated_count = 0
    skipped_decided = 0
    with container.uow as uow:
        decided = uow.decisions.decided_subject_ids(subject_ids)
        for rec in recs:
            if rec.subject_id in decided:
                skipped_decided += 1
                continue
            profile = profiles_map.get(rec.subject_id)
            if profile is None:
                continue
            profile.source = rec.origin
            profile.rating_token = rec.rating_token
            profile.origin = rec.origin
            profile.is_second_chance = rec.is_second_chance
            profile.second_chance_source = rec.second_chance_source
            existing = uow.profiles.get(rec.subject_id)
            if existing:
                existing.last_seen_at = datetime.now(timezone.utc)
                existing.times_seen += 1
                existing.rating_token = rec.rating_token
                existing.origin = rec.origin
                existing.is_second_chance = rec.is_second_chance
                existing.second_chance_source = rec.second_chance_source
                _copy_demographics(existing, profile)
                updated_count += 1
            else:
                uow.profiles.add(profile)
                new_count += 1
        uow.commit()

    log.info(
        "fetch_persist_done",
        fetched=len(recs),
        new=new_count,
        updated=updated_count,
        skipped_decided=skipped_decided,
    )
    return len(recs)


@router.get("/", response_model=HingeRecommendationsResponse)
async def get_recommendations(  # noqa: C901 — top-level route orchestrates several flows
    refresh: bool = Query(default=False),
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeRecommendationsResponse:
    """Return all undecided Hinge profiles from DB.

    Pass ``?refresh=true`` to fetch a fresh batch from Hinge upstream
    first, hydrate, persist, then return the full undecided queue.
    """
    total_fetched = 0

    # Ensure prompts cache is loaded (one-time lazy fetch)
    await container.ensure_prompts()

    if refresh:
        total_fetched = await _fetch_and_persist(container)

    # Load ALL undecided profiles from DB and hydrate content from API
    with container.uow as uow:
        all_profiles = uow.profiles.get_undecided()

    if all_profiles:
        try:
            await container.hinge_api.refresh_demographics(all_profiles)
        except Exception:
            log.warning(
                "demographics_refresh_failed",
                count=len(all_profiles),
                exc_info=True,
            )
        try:
            await container.hinge_api.hydrate_profiles(all_profiles)
        except Exception:
            log.warning(
                "hydrate_failed",
                count=len(all_profiles),
                exc_info=True,
            )

    # Build rating_token lookup from client state
    rec_state = container._client.recommendations

    # Cross-reference with standouts (ETag-cached, cheap)
    standout_ids: set[str] = set()
    try:
        standouts_resp = await container._client.get_standouts_v3()
        if standouts_resp:
            standout_ids = {s.subject_id for s in standouts_resp.standouts}
    except Exception:
        pass  # non-critical

    # Get user's own location for distance computation
    user_lat: float | None = None
    user_lon: float | None = None
    try:
        self_profile = await container._client.get_self_profile()
        loc = self_profile.profile.location
        user_lat = loc.latitude
        user_lon = loc.longitude
    except Exception:
        pass  # non-critical

    # Write-through: sync in-memory tokens to DB for skip/like
    tokens_to_sync: list[tuple[str, str, str]] = []
    for p in all_profiles:
        rec_info = rec_state.get(p.subject_id)
        if (
            rec_info
            and rec_info.rating_token
            and p.rating_token != rec_info.rating_token
        ):
            tokens_to_sync.append(
                (p.subject_id, rec_info.rating_token, rec_info.origin or "discover"),
            )
    if tokens_to_sync:
        with container.uow as uow:
            for sid, token, orig in tokens_to_sync:
                prof = uow.profiles.get(sid)
                if prof:
                    prof.rating_token = token
                    prof.origin = orig
            uow.commit()

    # Score each profile
    encounters: list[HingeEncounterOut] = []
    for p in all_profiles:
        try:
            score_val, reasoning = await container.scorer.score(p)
        except Exception:
            log.warning("score_failed", subject_id=p.subject_id[:12])
            score_val, reasoning = 0.0, ""

        # Use fresh rating_token if available, else DB token
        rec_info = rec_state.get(p.subject_id)
        rating_token = rec_info.rating_token if rec_info else (p.rating_token or "")
        origin = rec_info.origin if rec_info else (p.origin or p.source or "discover")

        encounters.append(
            _profile_to_encounter(
                p,
                rating_token,
                origin,
                score=round(score_val, 1),
                reasoning=reasoning,
                is_standout=p.subject_id in standout_ids,
                is_second_chance=p.is_second_chance,
                second_chance_source=p.second_chance_source,
                user_lat=user_lat,
                user_lon=user_lon,
            ),
        )

    # Get limits
    try:
        limit = await container.hinge_api.get_like_limit()
        likes_left = limit.likes_left
        superlikes_left = limit.superlikes_left
    except Exception:
        likes_left = None
        superlikes_left = None

    feed_exhausted = container._client.feed_exhausted

    # Auto-trigger rejection scan when refresh exhausts the feed
    if refresh and feed_exhausted:
        from hinge.application.services.rejection_scan import (
            exhaust_feed,
            scan_state,
        )

        if not scan_state.running:
            asyncio.create_task(
                exhaust_feed(container, trigger="feed_exhausted"),
            )
            log.info("rejection_scan_auto_triggered")

    log.info(
        "hinge_recommendations_loaded",
        count=len(encounters),
        fetched=total_fetched,
        exhausted=feed_exhausted,
    )
    return HingeRecommendationsResponse(
        encounters=encounters,
        total_fetched=total_fetched,
        total_undecided=len(encounters),
        filtered_already_decided=0,
        likes_left=likes_left,
        superlikes_left=superlikes_left,
        feed_exhausted=feed_exhausted,
    )


def _resolve_token(
    container: HingeContainer,
    subject_id: str,
) -> tuple[str, str]:
    """Resolve rating_token and origin from all available sources.

    Lookup order: in-memory recommendations → standout tokens → DB profile.
    Returns (rating_token, origin). Token is empty string if not found.
    """
    rec = container._client.recommendations.get(subject_id)
    if rec:
        return rec.rating_token, rec.origin or "discover"

    standout_tokens: dict[str, str] = getattr(
        container._client,
        "_standout_tokens",
        {},
    )
    if subject_id in standout_tokens:
        return standout_tokens[subject_id], "standouts"

    # Final fallback: DB profile (survives server restarts)
    with container.uow as uow:
        profile = uow.profiles.get(subject_id)
        if profile and profile.rating_token:
            return profile.rating_token, profile.origin or "discover"

    return "", "discover"


@router.post("/{subject_id}/skip", response_model=HingeLikeResponse)
async def skip_recommendation(
    subject_id: str,
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeLikeResponse:
    """Skip a recommendation."""
    rating_token, origin = _resolve_token(container, subject_id)

    if not rating_token:
        log.warning("skip_no_token", subject_id=subject_id[:12])
        return HingeLikeResponse(success=False)

    await container.hinge_api.skip(subject_id, rating_token, origin)
    log.info("recommendation_skipped", subject_id=subject_id[:12], origin=origin)

    with container.uow as uow:
        uow.decisions.add(
            HingeDecision(
                profile_subject_id=subject_id,
                action="skip",
            ),
        )
        uow.commit()

    return HingeLikeResponse(success=True)


@router.post("/{subject_id}/like", response_model=HingeLikeResponse)
async def like_recommendation(
    subject_id: str,
    body: HingeLikeRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeLikeResponse:
    """Like a photo or prompt on a recommendation."""
    rating_token, origin = _resolve_token(container, subject_id)

    if not rating_token:
        log.warning("like_no_token", subject_id=subject_id[:12])
        return HingeLikeResponse(success=False)

    if body.content_type == "photo":
        limit = await container.hinge_api.like_photo(
            subject_id=subject_id,
            rating_token=rating_token,
            origin=origin or "discover",
            content_id=body.content_id,
            url=body.url or "",
            cdn_id=body.cdn_id or "",
            comment=body.comment,
            superlike=body.superlike,
        )
    else:
        limit = await container.hinge_api.like_prompt(
            subject_id=subject_id,
            rating_token=rating_token,
            origin=origin or "discover",
            content_id=body.content_id,
            question=body.question or "",
            answer=body.answer or "",
            comment=body.comment,
            superlike=body.superlike,
        )

    action = "superlike" if body.superlike else ("note" if body.comment else "like")
    log.info(
        "recommendation_liked",
        subject_id=subject_id[:12],
        action=action,
        content_type=body.content_type,
        likes_left=limit.likes_left,
    )
    with container.uow as uow:
        uow.decisions.add(
            HingeDecision(
                profile_subject_id=subject_id,
                action=action,
                content_id=body.content_id,
                comment=body.comment,
            ),
        )
        uow.commit()

    return HingeLikeResponse(
        success=True,
        likes_left=limit.likes_left,
        superlikes_left=limit.superlikes_left,
    )


@router.post("/recycle")
async def recycle_profiles(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Recycle previously seen profiles."""
    await container.hinge_api.repeat_profiles()
    return {"success": True}
