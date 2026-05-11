"""Hinge preferences endpoints."""

from fastapi import APIRouter, Depends

from hinge.core.logging_config import logger as log
from hinge.api.deps import require_hinge_auth
from hinge.bootstrap import HingeContainer

router = APIRouter(prefix="/preferences", tags=["hinge-preferences"])


@router.get("/")
async def get_preferences(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Get current preferences."""
    result = await container.hinge_api.get_preferences()
    log.info("preferences_loaded")
    return result


@router.patch("/")
async def update_preferences(
    preferences: dict,
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Update preferences."""
    await container.hinge_api.update_preferences(preferences)
    log.info("preferences_updated", keys=list(preferences.keys()))
    return {"success": True}
