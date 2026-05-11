"""Main Hinge API router — aggregates all sub-routers."""

from fastapi import APIRouter

from hinge.api import (
    analytics,
    auth,
    chat,
    likes,
    matches,
    preferences,
    profile,
    recommendations,
    websocket,
)

router = APIRouter(prefix="/api/v1/hinge", tags=["hinge"])

router.include_router(recommendations.router)
router.include_router(likes.router)
router.include_router(matches.router)
router.include_router(chat.router)
router.include_router(profile.router)
router.include_router(preferences.router)
router.include_router(analytics.router)
router.include_router(auth.router)
router.include_router(websocket.router)
