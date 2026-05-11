"""Hinge match list endpoints."""

from fastapi import APIRouter, Depends

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.api.schemas import BlockMatchRequest, HingeMatchesResponse, HingeMatchOut
from hinge.bootstrap import HingeContainer

router = APIRouter(prefix="/matches", tags=["hinge-matches"])


@router.get("/", response_model=HingeMatchesResponse)
async def get_matches(
    container: HingeContainer = Depends(require_hinge_auth),
) -> HingeMatchesResponse:
    """Get match list."""
    matches = await container.hinge_api.get_matches()
    match_outs = [
        HingeMatchOut(
            subject_id=m.subject_id,
            first_name=m.profile.first_name if m.profile else "Unknown",
            age=m.profile.age if m.profile else None,
            photos=m.profile.photo_urls if m.profile else [],
            matched_at=m.matched_at,
            last_message=m.last_message_text,
            unread_count=m.unread_count,
        )
        for m in matches
    ]
    log.info("matches_loaded", count=len(match_outs))
    return HingeMatchesResponse(matches=match_outs, total=len(match_outs))


@router.post("/{subject_id}/block")
async def block_match(
    subject_id: str,
    body: BlockMatchRequest,
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Block/unmatch a match (with optional second chance eligibility)."""
    await container._client.block_match(
        subject_id,
        second_chance_eligible=body.second_chance_eligible,
    )
    log.info("match_blocked", subject_id=subject_id[:12])
    return {"success": True}
