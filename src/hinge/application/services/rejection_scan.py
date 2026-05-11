"""Background feed exhaustion for rejection detection.

Exhausts the entire rec/v2 feed to collect all available subject IDs,
then diffs against DB to find profiles that disappeared (likely rejected us).

IMPORTANT: 429 (rate limit) from rec/v2 returns empty JSON `{}` which looks
identical to feed exhaustion (0 subjects). The scan MUST check HTTP status
codes and retry on 429 instead of treating it as exhaustion. Failing to do
so causes massive false positives (82% in testing).
"""

import asyncio
from datetime import datetime, timezone

from httpx import HTTPStatusError

from hinge.core.logging_config import logger as log
from hinge.bootstrap import HingeContainer


class RejectionScanResult:
    """Result of a rejection scan."""

    def __init__(self, trigger: str = "manual") -> None:
        """Initialise an empty result tagged with how the scan was triggered."""
        self.total_fetched: int = 0
        self.unique_pool: int = 0
        self.batches: int = 0
        self.disappeared: int = 0
        self.marked_rejected: int = 0
        self.rate_limit_retries: int = 0
        self.error: str | None = None
        self.trigger: str = trigger
        self.started_at: datetime = datetime.now(timezone.utc)
        self.finished_at: datetime | None = None


class ScanState:
    """Shared mutable state for rejection scan progress.

    Both the manual trigger (analytics router) and the scheduled runner
    update this so the status endpoint always reflects reality.
    """

    def __init__(self) -> None:
        """Construct an idle scan state singleton."""
        self.running: bool = False
        self.current_run: RejectionScanResult | None = None
        self.last_result: RejectionScanResult | None = None


scan_state = ScanState()


def persist_scan_result(
    container: HingeContainer,
    result: RejectionScanResult,
) -> None:
    """Write scan result to the hinge_scan_runs table."""
    from hinge.infrastructure.db.tables.scan_run import hinge_scan_run_table

    with container.uow as uow:
        uow.session.execute(
            hinge_scan_run_table.insert().values(
                started_at=result.started_at,
                finished_at=result.finished_at,
                total_fetched=result.total_fetched,
                unique_pool=result.unique_pool,
                batches=result.batches,
                disappeared=result.disappeared,
                marked_rejected=result.marked_rejected,
                trigger=result.trigger,
                rate_limit_retries=result.rate_limit_retries,
                error=result.error,
            ),
        )
        uow.commit()


_MISS_THRESHOLD = 3  # consecutive scans absent before marking rejected


async def _exhaust_feed_phase1(
    container: HingeContainer,
    result: RejectionScanResult,
    *,
    delay_seconds: float,
    burst_size: int,
    burst_pause: float,
    max_rate_limit_retries: int,
    rate_limit_wait: float,
) -> set[str]:
    """Phase 1: Exhaust the rec/v2 feed, collecting all subject IDs."""
    pool: set[str] = set()
    calls_in_burst = 0
    consecutive_empty = 0
    rate_limit_retries = 0

    while True:
        try:
            recs = await container.hinge_api.get_recommendations()
        except HTTPStatusError as exc:
            if exc.response.status_code == 429:
                rate_limit_retries += 1
                result.rate_limit_retries += 1
                if rate_limit_retries > max_rate_limit_retries:
                    log.error(
                        "rejection_scan_rate_limit_exhausted",
                        retries=rate_limit_retries,
                        pool_size=len(pool),
                    )
                    result.error = (
                        f"Rate limited {rate_limit_retries} times, "
                        f"aborting with partial pool ({len(pool)})"
                    )
                    return pool
                log.warning(
                    "rejection_scan_rate_limited",
                    retry=rate_limit_retries,
                    wait_seconds=rate_limit_wait,
                    pool_size=len(pool),
                )
                await asyncio.sleep(rate_limit_wait)
                calls_in_burst = 0
                continue
            raise

        result.batches += 1
        batch_ids = {rec.subject_id for rec in recs}
        new_ids = batch_ids - pool
        pool.update(batch_ids)
        result.total_fetched += len(batch_ids)

        log.info(
            "rejection_scan_batch",
            batch=result.batches,
            batch_size=len(batch_ids),
            new=len(new_ids),
            pool_size=len(pool),
        )

        if len(batch_ids) == 0:
            consecutive_empty += 1
            if consecutive_empty >= 2:
                break
        else:
            consecutive_empty = 0
            rate_limit_retries = 0

        calls_in_burst += 1
        if calls_in_burst >= burst_size:
            log.info("rejection_scan_burst_pause", pause_seconds=burst_pause)
            await asyncio.sleep(burst_pause)
            calls_in_burst = 0
        else:
            await asyncio.sleep(delay_seconds)

    return pool


async def _classify_rejections(
    container: HingeContainer,
    subject_ids: set[str],
) -> dict[str, str]:
    """Classify newly rejected profiles as 'passed' or 'gone'.

    Calls ``/user/v2/public`` for each subject_id. If data comes back
    the user is still active (they passed on us); empty means gone.
    """
    classifications: dict[str, str] = {}
    for sid in subject_ids:
        try:
            v2_data = await container._client.get_profiles_v2([sid])
            if v2_data:
                classifications[sid] = "passed"
            else:
                classifications[sid] = "gone"
        except Exception:
            classifications[sid] = "gone"
        # Small delay to avoid hammering the API
        await asyncio.sleep(2)
    return classifications


def _find_newly_rejected(
    uow: object,
    disappeared: set[str],
) -> set[str]:
    """Find profiles that crossed the miss_count threshold this scan."""
    from sqlalchemy import select

    from hinge.infrastructure.db.tables.profile import hinge_profile_table

    stmt = select(hinge_profile_table.c.subject_id).where(
        hinge_profile_table.c.subject_id.in_(disappeared),
        hinge_profile_table.c.miss_count >= _MISS_THRESHOLD,
        hinge_profile_table.c.likely_rejected.is_(False),
    )
    return set(uow.session.execute(stmt).scalars())


async def _diff_and_track_misses(
    container: HingeContainer,
    result: RejectionScanResult,
    pool: set[str],
) -> None:
    """Phase 2: Diff pool against DB using consecutive miss tracking."""
    with container.uow as uow:
        db_undecided = uow.profiles.get_undecided_subject_ids()
        disappeared = db_undecided - pool
        still_present = db_undecided & pool
        result.disappeared = len(disappeared)

        # Clear false rejections — profiles that reappeared
        cleared = uow.profiles.clear_false_rejections(still_present)
        if cleared:
            log.info("rejection_scan_cleared_false", count=cleared)

        # Reset miss_count for profiles still in the feed
        uow.profiles.reset_miss_count(still_present)

        # Increment miss_count for absent profiles
        if disappeared:
            uow.profiles.increment_miss_count(disappeared)

        # Find profiles crossing the threshold this scan
        to_reject = _find_newly_rejected(uow, disappeared)
        if to_reject:
            result.marked_rejected = uow.profiles.mark_likely_rejected(
                to_reject,
            )

        uow.commit()

    # Phase 2b: Classify newly rejected profiles (async API calls)
    if to_reject:
        classifications = await _classify_rejections(container, to_reject)
        with container.uow as uow:
            for sid, rtype in classifications.items():
                uow.profiles.set_rejection_type(sid, rtype)
            uow.commit()
        log.info(
            "rejection_scan_classified",
            passed=sum(1 for v in classifications.values() if v == "passed"),
            gone=sum(1 for v in classifications.values() if v == "gone"),
        )

    log.info(
        "rejection_scan_complete",
        pool_size=result.unique_pool,
        batches=result.batches,
        db_undecided=len(db_undecided),
        disappeared=result.disappeared,
        marked=result.marked_rejected,
        cleared=cleared,
    )


async def _persist_discovered_profiles(
    container: HingeContainer,
    pool: set[str],
) -> int:
    """Persist new profiles discovered during the scan to DB."""
    # Find which pool IDs are not yet in DB
    new_ids: set[str] = set()
    with container.uow as uow:
        for sid in pool:
            if uow.profiles.get(sid) is None:
                new_ids.add(sid)
    if not new_ids:
        return 0

    # Batch fetch via quick profiles (v2 public endpoint)
    profiles_map = await container.hinge_api.get_profiles_quick(
        list(new_ids),
    )
    saved = 0
    with container.uow as uow:
        for profile in profiles_map.values():
            profile.source = "rejection_scan"
            uow.profiles.add(profile)
            saved += 1
        uow.commit()

    log.info("rejection_scan_profiles_saved", new=saved, pool=len(pool))
    return saved


async def exhaust_feed(
    container: HingeContainer,
    *,
    delay_seconds: float = 4.0,
    burst_size: int = 12,
    burst_pause: float = 35.0,
    max_rate_limit_retries: int = 5,
    rate_limit_wait: float = 35.0,
    trigger: str = "manual",
) -> RejectionScanResult:
    """Exhaust the rec/v2 feed and detect likely rejections.

    Uses consecutive miss tracking: profiles must be absent from
    _MISS_THRESHOLD consecutive successful scans before being marked
    as likely rejected. This prevents false positives from transient
    API caching, preference changes, or rate limits.

    Args:
        container: Authenticated Hinge container.
        delay_seconds: Delay between individual calls (4s is safe).
        burst_size: Number of calls before a longer pause.
        burst_pause: Pause duration after a burst (seconds).
        max_rate_limit_retries: Max 429 retries before aborting.
        rate_limit_wait: Wait time on 429 (Cloudflare 30s cooldown).
        trigger: How the scan was triggered ("manual" or "scheduled").

    Returns:
        RejectionScanResult with stats.

    """
    if scan_state.running:
        return RejectionScanResult(trigger=trigger)

    result = RejectionScanResult(trigger=trigger)
    scan_state.running = True
    scan_state.current_run = result

    try:
        pool = await _exhaust_feed_phase1(
            container,
            result,
            delay_seconds=delay_seconds,
            burst_size=burst_size,
            burst_pause=burst_pause,
            max_rate_limit_retries=max_rate_limit_retries,
            rate_limit_wait=rate_limit_wait,
        )
        result.unique_pool = len(pool)

        # Phase 1b: Persist new profiles discovered during scan
        try:
            await _persist_discovered_profiles(container, pool)
        except Exception:
            log.warning("rejection_scan_profile_persist_failed", exc_info=True)

        # Phase 2: Diff against DB — only if we got a meaningful pool
        if result.error:
            log.warning(
                "rejection_scan_skipping_diff",
                reason="partial_pool",
                pool_size=result.unique_pool,
            )
        else:
            await _diff_and_track_misses(container, result, pool)

        # Phase 3: Recycle to restore the feed
        await container.hinge_api.repeat_profiles()
        log.info("rejection_scan_feed_recycled")

    except Exception as exc:
        result.error = str(exc)
        log.error("rejection_scan_failed", error=str(exc))
        try:
            await container.hinge_api.repeat_profiles()
        except Exception:
            pass

    result.finished_at = datetime.now(timezone.utc)
    scan_state.running = False
    scan_state.current_run = None
    scan_state.last_result = result

    try:
        persist_scan_result(container, result)
    except Exception:
        log.warning("rejection_scan_persist_failed", exc_info=True)

    return result
