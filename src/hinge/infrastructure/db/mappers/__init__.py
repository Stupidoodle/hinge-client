"""Imperative SQLAlchemy mappings for Hinge domain models."""

from sqlalchemy import event
from sqlalchemy.orm import registry

from hinge.domain.models.chat_channel import HingeChatChannel
from hinge.domain.models.chat_message import HingeChatMessage
from hinge.domain.models.decision import HingeDecision
from hinge.domain.models.profile import HingeProfile
from hinge.domain.models.prompt import HingePrompt
from hinge.domain.models.swipe_session import HingeSwipeSession
from hinge.infrastructure.db.tables.chat_channel import hinge_chat_channel_table
from hinge.infrastructure.db.tables.chat_message import hinge_chat_message_table
from hinge.infrastructure.db.tables.decision import hinge_decision_table
from hinge.infrastructure.db.tables.profile import hinge_profile_table
from hinge.infrastructure.db.tables.prompt import hinge_prompt_table
from hinge.infrastructure.db.tables.scan_run import hinge_scan_run_table  # noqa: F401
from hinge.infrastructure.db.tables.session import hinge_session_table

hinge_mapper_registry = registry()


def _init_excluded_defaults(target: HingeProfile, _context: object) -> None:
    """Set defaults for fields excluded from the ORM mapping."""
    target.photos = []
    target.prompts = []
    target.polls = []
    target.video_prompt = None
    target.date_ideas = []
    target.is_second_chance = False
    target.second_chance_source = None


def start_hinge_mappers() -> None:
    """Register all Hinge imperative mappings.

    Must be called once at application startup before any ORM operations.
    Subsequent calls are silently ignored (idempotent).
    """
    if hinge_mapper_registry.mappers:
        return

    hinge_mapper_registry.map_imperatively(
        HingeProfile,
        hinge_profile_table,
        exclude_properties={
            "photos",
            "prompts",
            "polls",
            "video_prompt",
            "date_ideas",
            "is_second_chance",
            "second_chance_source",
        },
    )
    event.listen(HingeProfile, "load", _init_excluded_defaults)

    hinge_mapper_registry.map_imperatively(HingeDecision, hinge_decision_table)

    hinge_mapper_registry.map_imperatively(
        HingeSwipeSession,
        hinge_session_table,
    )

    hinge_mapper_registry.map_imperatively(
        HingeChatChannel,
        hinge_chat_channel_table,
    )

    hinge_mapper_registry.map_imperatively(
        HingeChatMessage,
        hinge_chat_message_table,
    )

    hinge_mapper_registry.map_imperatively(HingePrompt, hinge_prompt_table)
