"""Hinge incoming likes + standouts endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.api.recommendations import _profile_to_encounter
from hinge.api.schemas import (
    HiddenLikeOut,
    HingeLikeResponse,
    HingeLikesYouResponse,
    HingeStandoutEncounterOut,
    HingeStandoutsResponse,
    LikeImpressionOut,
    LikeSortOut,
    RespondToLikeRequest,
    RespondToLikeResponse,
    StandoutHighlight,
)
from hinge.bootstrap import HingeContainer
from hinge.domain.models.decision import HingeDecision
from hinge.domain.models.profile import HingeProfile
from hinge.models import LikeImpression

router = APIRouter(prefix="/likes", tags=["hinge-likes"])

# Frontend sort keys → Hinge API sort keys
_SORT_KEY_MAP: dict[str, str] = {
    "recent": "mostRecent",
    "your_type": "recommended",
    "last_active": "recentlyActive",
    "nearby": "nearby",
}


def _build_like_impression(
    imp: LikeImpression,
    profile: HingeProfile | None,
) -> LikeImpressionOut:
    """Merge impression metadata with hydrated profile data."""
    photos: list[str] = []
    prompts: list[dict] = []
    if profile:
        photos = [p.url for p in profile.photos if p.url]
        prompts = [
            {
                "content_id": p.content_id,
                "question_text": p.question_text,
                "response": p.response,
            }
            for p in profile.prompts
        ]
    return LikeImpressionOut(
        subject_id=imp.subject_id,
        created=imp.created,
        rating=imp.rating,
        source=imp.source,
        initiated_with=imp.initiated_with,
        hidden=imp.hidden,
        rating_token=imp.rating_token,
        expires=imp.expires,
        first_name=profile.first_name if profile else None,
        age=profile.age if profile else None,
        photos=photos,
        prompts=prompts,
        location_name=profile.location_name if profile else None,
        job_title=profile.job_title if profile else None,
    )


@router.get("/incoming", response_model=HingeLikesYouResponse)
async def get_incoming_likes(
    sort: str | None = Query(default=None),
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeLikesYouResponse:
    """Get profiles who liked you with sort options and hidden likes."""
    api_sort = _SORT_KEY_MAP.get(sort, sort) if sort else None
    data = await container._client.get_likes_received(sort=api_sort)

    # Hydrate profile data for all impressions
    subject_ids = [imp.subject_id for imp in data.likes]
    profiles_map = (
        await container.hinge_api.get_profiles_quick(
            subject_ids,
        )
        if subject_ids
        else {}
    )

    likes = [
        _build_like_impression(imp, profiles_map.get(imp.subject_id))
        for imp in data.likes
    ]
    sorts = [LikeSortOut(id=s.id, title=s.title) for s in data.sorts]
    hidden = [HiddenLikeOut(id=h.id, reason=h.reason) for h in data.hidden_likes]
    log.info(
        "likes_incoming_loaded",
        total=len(likes),
        hidden=len(hidden),
        sort=sort,
    )
    return HingeLikesYouResponse(
        likes=likes,
        sorts=sorts,
        hidden_likes=hidden,
        total=len(likes),
        view_token=data.view_token,
    )


@router.post(
    "/incoming/{subject_id}/respond",
    response_model=RespondToLikeResponse,
)
async def respond_to_like(
    subject_id: str,
    body: RespondToLikeRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> RespondToLikeResponse:
    """Respond to an incoming like (accept or block)."""
    if body.action not in ("like", "block"):
        raise HTTPException(
            status_code=400,
            detail="action must be 'like' or 'block'",
        )
    await container._client.respond_to_like(
        subject_id,
        body.action,
        sort_type=body.sort_type,
    )

    log.info("like_responded", subject_id=subject_id[:12], action=body.action)
    action = "like" if body.action == "like" else "block"
    with container.uow as uow:
        uow.decisions.add(
            HingeDecision(
                profile_subject_id=subject_id,
                action=action,
                is_match=body.action == "like",
            ),
        )
        uow.commit()

    return RespondToLikeResponse(success=True)


@router.get("/standouts", response_model=HingeStandoutsResponse)
async def get_standouts(
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeStandoutsResponse:
    """Get standouts feed (v2 for free/paid split), hydrated into encounters."""
    await container.ensure_prompts()

    # Use v2 to get the free/paid split
    response = await container._client.get_standouts()
    all_subjects = response.free + response.paid
    if not all_subjects:
        return HingeStandoutsResponse(status=response.status)

    paid_ids = {s.subject_id for s in response.paid}

    # Hydrate standout subjects into full profiles
    subject_ids = [s.subject_id for s in all_subjects]
    profiles_map = await container.hinge_api.get_profiles_quick(subject_ids)

    # Cross-reference: check which standouts are also in discover feed
    with container.uow as uow:
        discover_ids = uow.profiles.get_undecided_subject_ids()

    # Build rating_token + highlight lookup
    token_map = {s.subject_id: s.rating_token for s in all_subjects}
    highlight_map: dict[str, StandoutHighlight] = {}
    for s in all_subjects:
        if s.content and s.content.photo:
            highlight_map[s.subject_id] = StandoutHighlight(
                content_id=s.content.photo.content_id,
                photo_url=s.content.photo.url,
                prompt_id=s.content.photo.prompt_id,
            )

    # Get user's own location for distance
    user_lat: float | None = None
    user_lon: float | None = None
    try:
        self_profile = await container._client.get_self_profile()
        loc = self_profile.profile.location
        user_lat = loc.latitude
        user_lon = loc.longitude
    except Exception:
        pass

    standouts: list[HingeStandoutEncounterOut] = []
    for sid in subject_ids:
        profile = profiles_map.get(sid)
        if not profile:
            continue
        encounter = _profile_to_encounter(
            profile,
            token_map.get(sid, ""),
            "standouts",
            is_standout=True,
            user_lat=user_lat,
            user_lon=user_lon,
        )
        standouts.append(
            HingeStandoutEncounterOut(
                encounter=encounter,
                highlight=highlight_map.get(sid),
                in_discover_feed=sid in discover_ids,
                is_rose_required=sid in paid_ids,
            ),
        )

    # Cache rating tokens for skip endpoint
    container._client._standout_tokens = token_map

    log.info("standouts_loaded", count=len(standouts))
    return HingeStandoutsResponse(
        standouts=standouts,
        expiration=response.expiration,
        status=response.status,
    )


class StandoutSkipRequest(BaseModel):
    """Request body for skipping a standout (rating_token optional)."""

    rating_token: str | None = None


@router.post("/standouts/{subject_id}/skip", response_model=HingeLikeResponse)
async def skip_standout(
    subject_id: str,
    body: StandoutSkipRequest | None = None,
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeLikeResponse:
    """Skip a standout profile via the standard rating endpoint."""
    # Look up rating_token: body > cached from GET /standouts
    token = body.rating_token if body and body.rating_token else None
    if not token:
        cached = getattr(container._client, "_standout_tokens", {})
        token = cached.get(subject_id)
    if not token:
        raise HTTPException(
            status_code=400,
            detail="rating_token required (fetch standouts first)",
        )

    await container.hinge_api.skip(subject_id, token, "standouts")
    log.info("standout_skipped", subject_id=subject_id[:12])

    with container.uow as uow:
        uow.decisions.add(
            HingeDecision(
                profile_subject_id=subject_id,
                action="skip",
            ),
        )
        uow.commit()

    return HingeLikeResponse(success=True)
