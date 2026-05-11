"""Hinge profile endpoints."""

import asyncio
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.api.recommendations import _profile_to_encounter
from hinge.api.schemas import (
    AnswerUpdateItem,
    CdnTokenResponse,
    ContentSettingsRequest,
    ContentSettingsResponse,
    HingeEncounterOut,
    HingeLikeLimitResponse,
    PhotoReorderRequest,
    PromptCatalogItem,
    PromptCatalogResponse,
    PromptCategoryOut,
    PromptEvaluationRequest,
    PromptEvaluationResponse,
)
from hinge.bootstrap import HingeContainer
from hinge.models import AnswerContentPayload, ContentSettings, TextAnswer

router = APIRouter(prefix="/profile", tags=["hinge-profile"])


# --- Own Profile ---


@router.get("/me")
async def get_self_profile(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Full own profile (v3) with {value, visible} wrappers for toggleable fields."""
    data = await container._client.get_self_profile()
    log.info("self_profile_loaded")
    return data.model_dump(mode="json", by_alias=True)


@router.get("/me/content")
async def get_self_content(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Own content: photos (pHash, cdnId), answers (with AI feedback), polls, video."""
    data = await container._client.get_self_content()
    return data.model_dump(mode="json", by_alias=True)


@router.get("/me/completion")
async def get_profile_completion(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Profile completion state + missing basics."""
    state, missing = await asyncio.gather(
        container._client.get_profile_state(),
        container._client.get_profile_basics_missing(),
    )
    return {"state": state, "missing": missing}


class ProfileUpdateRequest(BaseModel):
    """Request body for PATCH /profile/me.

    Top-level fields (lastActiveOptIn, paused) and profile sub-object
    with toggleable {value, visible} wrappers.
    """

    last_active_opt_in: bool | None = None
    paused: bool | None = None
    profile: dict[str, Any] | None = None


@router.patch("/me")
async def update_self_profile(
    body: ProfileUpdateRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Update own profile via PATCH /user/v2.

    Accepts toggleable fields as ``{value, visible}`` wrappers and
    plain fields as direct values.
    """
    payload: dict[str, Any] = {}
    if body.last_active_opt_in is not None:
        payload["lastActiveOptIn"] = body.last_active_opt_in
    if body.paused is not None:
        payload["paused"] = body.paused
    if body.profile:
        payload["profile"] = body.profile

    if not payload:
        return {"success": True}

    # v3 PATCH accepts a single object (not array-wrapped like v2)
    response = await container._client.client.patch(
        "/user/v3",
        json=payload,
        headers=container._client._get_default_headers(),
    )
    response.raise_for_status()
    log.info("self_profile_updated", fields=list(payload.keys()))
    return {"success": True}


# --- Limits & Settings ---


@router.get("/limits", response_model=HingeLikeLimitResponse)
async def get_limits(
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeLikeLimitResponse:
    """Get like/superlike limits."""
    limit = await container.hinge_api.get_like_limit()
    return HingeLikeLimitResponse(
        likes_left=limit.likes_left,
        superlikes_left=limit.superlikes_left,
        free_superlikes_left=limit.free_superlikes_left,
        free_superlike_expiration=limit.free_superlike_expiration,
    )


@router.post(
    "/evaluate-prompt",
    response_model=PromptEvaluationResponse,
)
async def evaluate_prompt(
    body: PromptEvaluationRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> PromptEvaluationResponse:
    """AI evaluation of a prompt answer for profile optimization."""
    result = await container._client.evaluate_prompt_answer(
        body.prompt_id,
        body.answer,
    )
    return PromptEvaluationResponse(
        evaluation=result.evaluation,
        detail=result.detail,
        feedback_token=result.feedback_token,
    )


@router.get(
    "/content-settings",
    response_model=ContentSettingsResponse,
)
async def get_content_settings(
    container: HingeContainer = Depends(require_hinge_auth),
) -> ContentSettingsResponse:
    """Get content settings (Smart Photo + Convo Starters)."""
    settings = await container._client.get_content_settings()
    return ContentSettingsResponse(
        is_smart_photo_opt_in=settings.is_smart_photo_opt_in,
        is_convo_starters_opt_in=settings.is_convo_starters_opt_in,
    )


@router.patch(
    "/content-settings",
    response_model=ContentSettingsResponse,
)
async def update_content_settings(
    body: ContentSettingsRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> ContentSettingsResponse:
    """Toggle Smart Photo ordering and/or Convo Starters."""
    current = await container._client.get_content_settings()
    updated = ContentSettings(
        is_smart_photo_opt_in=(
            body.is_smart_photo_opt_in
            if body.is_smart_photo_opt_in is not None
            else current.is_smart_photo_opt_in
        ),
        is_convo_starters_opt_in=(
            body.is_convo_starters_opt_in
            if body.is_convo_starters_opt_in is not None
            else current.is_convo_starters_opt_in
        ),
    )
    result = await container._client.update_content_settings(updated)
    return ContentSettingsResponse(
        is_smart_photo_opt_in=result.is_smart_photo_opt_in,
        is_convo_starters_opt_in=result.is_convo_starters_opt_in,
    )


# --- Photo Management ---


@router.put("/me/photos")
async def reorder_photos(
    body: PhotoReorderRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Reorder photos by content ID list.

    Sends the full photo array to ``PUT /content/v1/photos`` in the
    requested order.  All existing photos must be included — omitting
    one deletes it (use the DELETE endpoint for that).
    """
    content = await container._client.get_self_content()
    photos_by_id = {p.content_id: p for p in content.content.photos}

    missing = [cid for cid in body.content_ids if cid not in photos_by_id]
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown content_ids: {missing}",
        )

    ordered = [
        photos_by_id[cid].model_dump(mode="json", by_alias=True)
        for cid in body.content_ids
    ]
    result = await container._client.put_photos(ordered)
    log.info("photos_reordered", count=len(ordered))
    return result


@router.delete("/me/photos/{content_id}")
async def delete_photo(
    content_id: str,
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Delete a single photo by content ID.

    Fetches current photos, removes the target, and sends the
    remaining array via ``PUT /content/v1/photos``.
    Hinge requires a minimum of 6 photos.
    """
    content = await container._client.get_self_content()
    current = content.content.photos

    remaining = [p for p in current if p.content_id != content_id]
    if len(remaining) == len(current):
        raise HTTPException(status_code=404, detail="Photo not found")

    if len(remaining) < 6:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete — minimum 6 photos required",
        )

    payload = [p.model_dump(mode="json", by_alias=True) for p in remaining]
    result = await container._client.put_photos(payload)
    log.info("photo_deleted", content_id=content_id[:12], remaining=len(remaining))
    return result


@router.post(
    "/me/photos/upload-token",
    response_model=CdnTokenResponse,
)
async def get_upload_token(
    container: HingeContainer = Depends(require_hinge_auth),
) -> CdnTokenResponse:
    """Get a Cloudinary upload token for photo uploads."""
    data = await container._client.get_cdn_token()
    return CdnTokenResponse.model_validate(data)


# --- Prompts & Answers ---


@router.get("/prompts", response_model=PromptCatalogResponse)
async def get_prompt_catalog(
    container: HingeContainer = Depends(require_hinge_auth),
) -> PromptCatalogResponse:
    """Full prompt catalog (419 prompts, 14 categories) for the picker UI."""
    manager = await container._client.fetch_prompts()
    data = manager.prompts_data
    return PromptCatalogResponse(
        prompts=[
            PromptCatalogItem(
                id=p.id,
                prompt=p.prompt,
                is_selectable=p.is_selectable,
                placeholder=p.placeholder,
                is_new=p.is_new,
                categories=p.categories,
                content_types=[ct.value for ct in p.content_types],
            )
            for p in data.prompts
        ],
        categories=[
            PromptCategoryOut(
                name=c.name,
                slug=c.slug,
                is_visible=c.is_visible,
                is_new=c.is_new,
            )
            for c in data.categories
        ],
    )


@router.put("/answers")
async def update_answers(
    body: list[AnswerUpdateItem],
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Update prompt answers (full replacement — send all 3 positions).

    Each item needs ``position`` (0-2), ``question_id`` (prompt UUID),
    and ``response`` (answer text).
    """
    payloads = [
        AnswerContentPayload(
            position=item.position,
            question_id=item.question_id,
            text_answer=TextAnswer(
                response=item.response,
                question_id=item.question_id,
            ),
        )
        for item in body
    ]
    await container._client.update_answers(payloads)
    log.info("answers_updated", count=len(payloads))
    return {"success": True}


# --- Fresh Start ---


@router.get("/freshstart/eligible")
async def get_fresh_start_eligible(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Check if the account is eligible for a fresh start."""
    eligible = await container._client.get_fresh_start_eligible()
    return {"eligible": eligible}


@router.post("/freshstart")
async def do_fresh_start(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Execute a fresh start — resets the account."""
    await container._client.do_fresh_start()
    log.warning("fresh_start_executed")
    return {"success": True}


# --- Public Profile Lookup (must be LAST — catch-all path param) ---


@router.get("/{subject_id}", response_model=HingeEncounterOut)
async def get_profile(
    subject_id: str,
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeEncounterOut:
    """Fetch fresh profile + content from Hinge (single v2 call) and update DB."""
    await container.ensure_prompts()
    profiles_map = await container.hinge_api.get_profiles_quick(
        [subject_id],
    )
    profile = profiles_map.get(subject_id)

    # Fall back to DB if live API returned empty (transient visibility)
    if profile is None:
        with container.uow as uow:
            profile = uow.profiles.get(subject_id)
        if profile is None:
            raise HTTPException(status_code=404, detail="Profile not found")

    # Update DB if we have this profile stored
    with container.uow as uow:
        existing = uow.profiles.get(subject_id)
        if existing:
            existing.last_seen_at = datetime.now(timezone.utc)
            existing.times_seen += 1
            uow.commit()

    # Look up rating token from client state
    rec_info = container._client.recommendations.get(subject_id)
    rating_token = rec_info.rating_token if rec_info else ""
    origin = rec_info.origin if rec_info else (profile.source or "discover")

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

    log.info("profile_fetched", subject_id=subject_id[:12])
    return _profile_to_encounter(
        profile,
        rating_token,
        origin,
        user_lat=user_lat,
        user_lon=user_lon,
    )
