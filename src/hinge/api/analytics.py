"""Hinge analytics endpoints."""

import asyncio

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc, select

from hinge.core.logging_config import logger as log
from hinge.api.deps import get_hinge_container, require_hinge_auth
from hinge.api.schemas import HingeDashboardResponse
from hinge.application.services.rejection_scan import (
    exhaust_feed,
    scan_state,
)
from hinge.application.services.rejection_scheduler import DEFAULT_INTERVAL_HOURS
from hinge.bootstrap import HingeContainer
from hinge.infrastructure.db.tables.scan_run import hinge_scan_run_table

router = APIRouter(prefix="/analytics", tags=["hinge-analytics"])


@router.get("/dashboard", response_model=HingeDashboardResponse)
async def get_dashboard(
    container: HingeContainer = Depends(get_hinge_container),
) -> HingeDashboardResponse:
    """Dashboard metrics (total seen, liked, skipped, match rate).

    ``total_likes`` is the aggregate of ALL outgoing engagement actions
    (plain likes + notes + superlikes/roses).
    """
    with container.uow as uow:
        total_profiles = uow.profiles.count()
        plain_likes = uow.decisions.count_by_action("like")
        total_skips = uow.decisions.count_by_action("skip")
        total_notes = uow.decisions.count_by_action("note")
        total_superlikes = uow.decisions.count_by_action("superlike")
        total_matches = uow.decisions.count_matches()
        total_likely_rejected = uow.profiles.count_by_rejection_type("passed")
        total_account_removed = uow.profiles.count_by_rejection_type("gone")

    # All outgoing engagement actions are "likes" in aggregate
    total_likes = plain_likes + total_notes + total_superlikes
    match_rate = (total_matches / total_likes * 100) if total_likes > 0 else 0.0

    # Try to get live limits
    likes_remaining = None
    superlikes_remaining = None
    try:
        limit = await container.hinge_api.get_like_limit()
        likes_remaining = limit.likes_left
        superlikes_remaining = limit.superlikes_left
    except Exception:
        pass

    log.info(
        "dashboard_loaded",
        profiles=total_profiles,
        likes=total_likes,
        skips=total_skips,
        matches=total_matches,
        rate=round(match_rate, 1),
    )
    return HingeDashboardResponse(
        total_profiles_seen=total_profiles,
        total_likes=total_likes,
        total_skips=total_skips,
        total_notes=total_notes,
        total_superlikes=total_superlikes,
        total_matches=total_matches,
        match_rate=round(match_rate, 1),
        likes_remaining=likes_remaining,
        superlikes_remaining=superlikes_remaining,
        total_likely_rejected=total_likely_rejected,
        total_account_removed=total_account_removed,
    )


@router.get("/decisions")
async def get_decisions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Decision history with profile data (who you liked/skipped)."""
    with container.uow as uow:
        rows = uow.decisions.list_with_profiles(limit=limit, offset=offset)
        total = uow.decisions.count()
    return {"decisions": rows, "total": total}


@router.get("/daily-stats")
async def get_daily_stats(
    days: int = Query(default=30, ge=1, le=90),
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Daily aggregated stats for charting."""
    with container.uow as uow:
        stats = uow.decisions.daily_stats(since_days=days)
        avg = uow.decisions.avg_score()
    return {"daily": stats, "avg_score": round(avg, 1)}


@router.post("/rejection-scan")
async def start_rejection_scan(
    container: HingeContainer = Depends(require_hinge_auth),
) -> dict:
    """Trigger a background feed exhaustion to detect rejections."""
    if scan_state.running:
        return {"state": "already_running"}

    asyncio.create_task(exhaust_feed(container, trigger="manual"))
    log.info("rejection_scan_started")
    return {"state": "started"}


def _scan_row_to_dict(row) -> dict:
    """Convert a DB scan_run row mapping to a serializable dict."""
    return {
        "id": row["id"],
        "started_at": str(row["started_at"]) if row["started_at"] else None,
        "finished_at": str(row["finished_at"]) if row["finished_at"] else None,
        "total_fetched": row["total_fetched"],
        "unique_pool": row["unique_pool"],
        "batches": row["batches"],
        "disappeared": row["disappeared"],
        "marked_rejected": row["marked_rejected"],
        "trigger": row["trigger"],
        "error": row["error"],
    }


def _get_recent_runs(container: HingeContainer, limit: int = 10) -> list[dict]:
    """Fetch recent scan runs from DB."""
    try:
        with container.uow as uow:
            stmt = (
                select(hinge_scan_run_table)
                .order_by(desc(hinge_scan_run_table.c.started_at))
                .limit(limit)
            )
            rows = uow.session.execute(stmt).mappings().all()
        return [_scan_row_to_dict(r) for r in rows]
    except Exception:
        return []


@router.get("/rejection-scan/status")
async def get_rejection_scan_status(
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Check status of the running or last rejection scan.

    Includes live progress during active scans and recent run history.
    """
    base = {"interval_hours": DEFAULT_INTERVAL_HOURS}
    recent = _get_recent_runs(container)

    if scan_state.running and scan_state.current_run is not None:
        r = scan_state.current_run
        return {
            **base,
            "state": "running",
            "trigger": r.trigger,
            "total_fetched": r.total_fetched,
            "unique_pool": r.unique_pool,
            "batches": r.batches,
            "started_at": r.started_at.isoformat(),
            "recent_runs": recent,
        }

    if scan_state.last_result is not None:
        r = scan_state.last_result
        return {
            **base,
            "state": "completed" if r.error is None else "error",
            "total_fetched": r.total_fetched,
            "unique_pool": r.unique_pool,
            "batches": r.batches,
            "disappeared": r.disappeared,
            "marked_rejected": r.marked_rejected,
            "error": r.error,
            "trigger": r.trigger,
            "recent_runs": recent,
        }

    # Fall back to DB for last persisted scan
    if recent:
        last = recent[0]
        return {
            **base,
            "state": "completed" if last["error"] is None else "error",
            **{
                k: last[k]
                for k in (
                    "total_fetched",
                    "unique_pool",
                    "batches",
                    "disappeared",
                    "marked_rejected",
                    "error",
                    "trigger",
                    "finished_at",
                )
            },
            "recent_runs": recent,
        }

    return {**base, "state": "idle", "recent_runs": []}


@router.get("/rejection-scan/history")
async def get_rejection_scan_history(
    limit: int = Query(default=10, ge=1, le=50),
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """Return last N rejection scan runs from DB."""
    return {"runs": _get_recent_runs(container, limit=limit)}


@router.get("/rejections")
async def get_rejections(
    container: HingeContainer = Depends(get_hinge_container),
) -> dict:
    """List profiles that likely rejected/passed on us."""
    with container.uow as uow:
        profiles = uow.profiles.get_likely_rejected()

    return {
        "total": len(profiles),
        "profiles": [
            {
                "subject_id": p.subject_id,
                "first_name": p.first_name,
                "age": p.age,
                "rejection_detected_at": (
                    p.rejection_detected_at.isoformat()
                    if p.rejection_detected_at
                    else None
                ),
                "rejection_type": p.rejection_type,
                "first_seen_at": p.first_seen_at.isoformat(),
                "times_seen": p.times_seen,
                "photo_urls": p.photo_urls,
            }
            for p in profiles
        ],
    }
