"""Hinge profile domain model."""

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class ProfilePrompt:
    """A prompt/question answer on a Hinge profile.

    Covers text, voice, and video answer types.
    """

    question_id: str
    question_text: str
    response: str | None = None
    content_type: str = "text"  # text | voice | video
    content_id: str | None = None
    position: int | None = None
    # Voice answer fields
    audio_url: str | None = None
    waveform: str | None = None  # pipe-delimited amplitudes
    transcription: str | None = None
    # Video answer fields
    video_url: str | None = None
    thumbnail_url: str | None = None


@dataclass
class ProfileVideoDetail:
    """An embedded video variant (sd/hd) on a photo."""

    url: str
    width: int | None = None
    height: int | None = None
    quality: str | None = None  # "sd" | "hd"


@dataclass
class ProfilePhoto:
    """A photo on a Hinge profile."""

    content_id: str
    cdn_id: str
    url: str
    width: int | None = None
    height: int | None = None
    p_hash: str | None = None
    selfie_verified: bool = False
    video_url: str | None = None
    videos: list[ProfileVideoDetail] = field(default_factory=list)
    caption: str | None = None
    location: str | None = None
    prompt_id: str | None = None


@dataclass
class ProfilePoll:
    """A prompt poll on a Hinge profile."""

    content_id: str
    question_id: str
    question_text: str
    options: list[str] = field(default_factory=list)
    selected_option_index: int | None = None


@dataclass
class ProfileVideoPrompt:
    """A standalone video prompt on a Hinge profile."""

    content_id: str
    question_id: str | None = None
    question_text: str = ""
    video_url: str | None = None
    thumbnail_url: str | None = None
    cdn_id: str | None = None


@dataclass
class ProfileDateIdea:
    """A date idea prompt on a Hinge profile."""

    content_id: str
    question_id: str | None = None
    question_text: str = ""
    options: list[str] = field(default_factory=list)


@dataclass
class HingeProfile:
    """Domain profile — stable business entity, persisted to DB."""

    subject_id: str
    first_name: str
    age: int | None = None
    gender_id: int | None = None
    height: int | None = None
    location_name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    hometown: str | None = None
    job_title: str | None = None
    works: str | None = None
    education_attained: int | None = None
    selfie_verified: bool = False
    did_just_join: bool = False
    last_active_status_id: int | None = None

    # Lifestyle enums (stored as int IDs)
    children: int | None = None
    dating_intention: int | None = None
    dating_intention_text: str | None = None
    drinking: int | None = None
    drugs: int | None = None
    marijuana: int | None = None
    smoking: int | None = None
    family_plans: int | None = None
    politics: int | None = None
    religions: list[int] = field(default_factory=list)
    ethnicities: list[int] = field(default_factory=list)
    ethnicities_text: str | None = None
    relationship_types: list[int] = field(default_factory=list)
    relationship_types_text: str | None = None
    languages_spoken: list[int] = field(default_factory=list)
    pets: list[int] = field(default_factory=list)
    zodiac: int | None = None
    educations: str | None = None
    last_active_status: str | None = None

    # Content
    photos: list[ProfilePhoto] = field(default_factory=list)
    prompts: list[ProfilePrompt] = field(default_factory=list)
    polls: list[ProfilePoll] = field(default_factory=list)
    video_prompt: ProfileVideoPrompt | None = None
    date_ideas: list[ProfileDateIdea] = field(default_factory=list)
    photo_urls: list[str] = field(default_factory=list)

    # Second chance (recycled profile reappearing)
    is_second_chance: bool = False
    second_chance_source: int | None = None

    # Rejection detection
    likely_rejected: bool = False
    rejection_detected_at: datetime | None = None
    rejection_type: str | None = None  # "passed" | "gone"
    miss_count: int = 0

    # Rating context (needed for like/skip API calls)
    rating_token: str | None = None
    origin: str | None = None

    # Lifecycle tracking
    first_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc),
    )
    times_seen: int = 1
    source: str | None = None
