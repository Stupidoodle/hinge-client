"""Scheduled rejection scan runner.

Simple asyncio loop that runs every ``interval_hours``.  Started
as a fire-and-forget task from app lifespan; respects the existing
``_active_scan`` guard in the analytics router.
"""

import asyncio

from hinge.core.logging_config import logger as log
from hinge.application.services.rejection_scan import exhaust_feed
from hinge.bootstrap import HingeContainer

# Default: run every 30 min (scan takes ~3-4 min, so ~48 runs/day)
DEFAULT_INTERVAL_HOURS = 0.5


async def run_scheduled_scans(
    container: HingeContainer,
    *,
    interval_hours: float = DEFAULT_INTERVAL_HOURS,
) -> None:
    """Background loop that triggers a rejection scan on a fixed interval.

    Checks that the Hinge client is authenticated before each run.
    Swallows all exceptions so the loop never dies.
    """
    interval_seconds = interval_hours * 3600

    # Wait one full interval before the first scheduled run
    # (avoids scanning immediately on startup)
    log.info(
        "rejection_scheduler_started",
        interval_hours=interval_hours,
    )
    await asyncio.sleep(interval_seconds)

    while True:
        try:
            # Only run if authenticated
            if not container._client.hinge_token:
                log.info("rejection_scheduler_skipped_no_auth")
                await asyncio.sleep(interval_seconds)
                continue

            log.info("rejection_scheduler_triggering")
            await exhaust_feed(container, trigger="scheduled")
            log.info("rejection_scheduler_run_complete")

        except asyncio.CancelledError:
            log.info("rejection_scheduler_cancelled")
            return
        except Exception:
            log.error("rejection_scheduler_error", exc_info=True)

        await asyncio.sleep(interval_seconds)
