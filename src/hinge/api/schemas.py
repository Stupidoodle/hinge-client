"""Hinge API response schemas."""

from datetime import datetime

from pydantic import BaseModel


class VideoDetailOut(BaseModel):
    """Embedded video variant (sd/hd) on a photo."""

    url: str
    width: int | None = None
    height: int | None = None
    quality: str | None = None


class PhotoDetailOut(BaseModel):
    """Photo detail for encounter cards."""

    content_id: str
    cdn_id: str
    url: str
    p_hash: str | None = None
    caption: str | None = None
    location: str | None = None
    prompt_id: str | None = None
    video_url: str | None = None
    videos: list[VideoDetailOut] = []


class PromptOut(BaseModel):
    """Prompt/answer for encounter cards."""

    content_id: str | None = None
    question_id: str
    question_text: str
    response: str | None = None
    content_type: str = "text"
    position: int | None = None
    # Voice answer fields
    audio_url: str | None = None
    waveform: str | None = None
    transcription: str | None = None
    # Video answer fields
    video_url: str | None = None
    thumbnail_url: str | None = None


class PollOut(BaseModel):
    """Prompt poll for encounter cards."""

    content_id: str
    question_id: str
    question_text: str
    options: list[str] = []
    selected_option_index: int | None = None


class VideoPromptOut(BaseModel):
    """Standalone video prompt on a profile."""

    content_id: str
    question_id: str | None = None
    question_text: str = ""
    video_url: str | None = None
    thumbnail_url: str | None = None
    cdn_id: str | None = None


class DateIdeaOut(BaseModel):
    """Date idea prompt on a profile."""

    content_id: str
    question_id: str | None = None
    question_text: str = ""
    options: list[str] = []


class ContentItemOut(BaseModel):
    """Likeable item on an encounter card.

    Supports all content types: photo, prompt (text), voice,
    video, poll, video_prompt, date_idea.
    """

    content_id: str
    type: str  # photo | prompt | voice | video | poll | video_prompt | date_idea
    position: int | None = None
    # Photo fields
    url: str | None = None
    cdn_id: str | None = None
    caption: str | None = None
    photo_location: str | None = None
    prompt_id: str | None = None
    # Prompt (text) fields
    question: str | None = None
    answer: str | None = None
    # Voice fields
    audio_url: str | None = None
    waveform: str | None = None
    transcription: str | None = None
    # Video fields
    video_url: str | None = None
    thumbnail_url: str | None = None
    # Poll fields
    options: list[str] | None = None
    selected_option_index: int | None = None


class HingeEncounterOut(BaseModel):
    """Full encounter card for the recommendation feed."""

    subject_id: str
    first_name: str
    age: int | None = None
    photos: list[str] = []
    photo_details: list[PhotoDetailOut] = []
    prompts: list[PromptOut] = []
    polls: list[PollOut] = []
    location: str | None = None
    job_title: str | None = None
    height: int | None = None
    selfie_verified: bool = False
    did_just_join: bool = False
    last_active_status: str | None = None
    last_active_status_id: int | None = None
    # Lifestyle (all resolved to display labels)
    hometown: str | None = None
    works: str | None = None
    educations: str | None = None
    education_attained: str | None = None
    children: str | None = None
    dating_intention: str | None = None
    dating_intention_text: str | None = None
    family_plans: str | None = None
    relationship_types: str | None = None
    relationship_types_text: str | None = None
    drinking: str | None = None
    smoking: str | None = None
    drugs: str | None = None
    marijuana: str | None = None
    religions: str | None = None
    politics: str | None = None
    ethnicities: str | None = None
    ethnicities_text: str | None = None
    languages_spoken: str | None = None
    pets: str | None = None
    zodiac: str | None = None
    # Scoring
    score: float | None = None
    reasoning: str | None = None
    # Rating context
    rating_token: str = ""
    origin: str = ""
    content_items: list[ContentItemOut] = []
    # Standalone content
    video_prompt: VideoPromptOut | None = None
    date_ideas: list[DateIdeaOut] = []
    # Distance
    distance_km: float | None = None
    # Cross-reference
    is_standout: bool = False
    # Second chance (recycled profile)
    is_second_chance: bool = False
    second_chance_source: int | None = None


class HingeRecommendationsResponse(BaseModel):
    """Response for the recommendations endpoint."""

    encounters: list[HingeEncounterOut]
    total_fetched: int
    total_undecided: int = 0
    filtered_already_decided: int = 0
    likes_left: int | None = None
    superlikes_left: int | None = None
    feed_exhausted: bool = False


class HingeLikeRequest(BaseModel):
    """Request body for liking a photo/prompt."""

    content_id: str
    content_type: str  # "photo" or "prompt"
    comment: str | None = None
    superlike: bool = False
    # For photos
    url: str | None = None
    cdn_id: str | None = None
    # For prompts
    question: str | None = None
    answer: str | None = None


class HingeLikeResponse(BaseModel):
    """Response after liking/skipping."""

    success: bool
    is_match: bool = False
    likes_left: int = 0
    superlikes_left: int = 0


class HingeMatchOut(BaseModel):
    """A match in the match list."""

    subject_id: str
    first_name: str
    age: int | None = None
    photos: list[str] = []
    matched_at: datetime | None = None
    last_message: str | None = None
    unread_count: int = 0


class HingeMatchesResponse(BaseModel):
    """Response for the matches endpoint."""

    matches: list[HingeMatchOut]
    total: int


class HingeLikeLimitResponse(BaseModel):
    """Response for the like limit endpoint."""

    likes_left: int
    superlikes_left: int
    free_superlikes_left: int | None = None
    free_superlike_expiration: datetime | None = None


class HingeProfileResponse(BaseModel):
    """Response for profile endpoints."""

    subject_id: str
    first_name: str
    age: int | None = None
    photos: list[str] = []
    prompts: list[PromptOut] = []
    location: str | None = None
    job_title: str | None = None
    height: int | None = None
    selfie_verified: bool = False


class HingeDashboardResponse(BaseModel):
    """Response for the analytics dashboard.

    ``total_likes`` is the aggregate of ALL outgoing engagement actions
    (plain likes + notes + superlikes/roses).  Breakdown fields
    ``total_notes`` and ``total_superlikes`` are provided separately.
    """

    total_profiles_seen: int
    total_likes: int
    total_skips: int
    total_notes: int
    total_superlikes: int
    total_matches: int
    match_rate: float
    likes_remaining: int | None = None
    total_likely_rejected: int = 0
    total_account_removed: int = 0
    superlikes_remaining: int | None = None


class HingeAuthStatusResponse(BaseModel):
    """Response for auth status check."""

    connected: bool
    identity_id: str | None = None
    token_expires: datetime | None = None
    sendbird_connected: bool = False


class HingeStandoutOut(BaseModel):
    """A standout profile with highlighted content."""

    subject_id: str
    rating_token: str
    photo_url: str | None = None
    content_id: str | None = None
    prompt_id: str | None = None
    is_paid: bool = False


class StandoutHighlight(BaseModel):
    """The featured "standout moment" content for a standout profile."""

    content_id: str | None = None
    photo_url: str | None = None
    prompt_id: str | None = None


class HingeStandoutEncounterOut(BaseModel):
    """A standout as a full encounter card + standout metadata."""

    encounter: HingeEncounterOut
    highlight: StandoutHighlight | None = None
    in_discover_feed: bool = False
    is_rose_required: bool = False


class HingeStandoutsResponse(BaseModel):
    """Response for the standouts endpoint (v3, hydrated)."""

    standouts: list[HingeStandoutEncounterOut] = []
    expiration: datetime | None = None
    status: str | None = None
    cached: bool = False


# --- Likes You ---


class LikeImpressionOut(BaseModel):
    """An incoming like (impression) with hydrated profile data."""

    subject_id: str
    created: str | None = None
    rating: str | None = None
    source: str | None = None
    initiated_with: str | None = None
    hidden: bool = False
    rating_token: str | None = None
    expires: str | None = None
    # Hydrated profile fields
    first_name: str | None = None
    age: int | None = None
    photos: list[str] = []
    prompts: list[dict] = []
    location_name: str | None = None
    job_title: str | None = None


class LikeSortOut(BaseModel):
    """Sort option for Likes You."""

    id: str
    title: str


class HiddenLikeOut(BaseModel):
    """A moderation-hidden like."""

    id: str
    reason: str | None = None


class HingeLikesYouResponse(BaseModel):
    """Response for GET /likes/incoming (Likes You)."""

    likes: list[LikeImpressionOut] = []
    sorts: list[LikeSortOut] = []
    hidden_likes: list[HiddenLikeOut] = []
    total: int = 0
    view_token: str | None = None


class RespondToLikeRequest(BaseModel):
    """Request body for responding to an incoming like."""

    action: str  # "like" or "block"
    sort_type: str | None = None


class RespondToLikeResponse(BaseModel):
    """Response after responding to an incoming like."""

    success: bool


class BlockMatchRequest(BaseModel):
    """Request body for blocking/unmatching."""

    second_chance_eligible: bool = False


# --- AI Evaluation ---


class PromptEvaluationRequest(BaseModel):
    """Request body for AI prompt evaluation."""

    prompt_id: str
    answer: str


class PromptEvaluationResponse(BaseModel):
    """Response from AI prompt evaluation."""

    evaluation: str | None = None
    detail: str | None = None
    feedback_token: str | None = None


# --- Content Settings ---


class ContentSettingsResponse(BaseModel):
    """Content settings (Smart Photo + Convo Starters)."""

    is_smart_photo_opt_in: bool = False
    is_convo_starters_opt_in: bool = False


class ContentSettingsRequest(BaseModel):
    """Request body for updating content settings."""

    is_smart_photo_opt_in: bool | None = None
    is_convo_starters_opt_in: bool | None = None


# --- Photo Management ---


class PhotoReorderRequest(BaseModel):
    """Request body for reordering photos. Ordered list of content IDs."""

    content_ids: list[str]


class CdnTokenResponse(BaseModel):
    """Response from POST /cdn/token."""

    token: str
    timestamp: str | int
    key: str
    expires: str | int | None = None


# --- Prompts & Answers ---


class PromptCatalogItem(BaseModel):
    """A single prompt from the catalog."""

    id: str
    prompt: str
    is_selectable: bool
    placeholder: str = ""
    is_new: bool = False
    categories: list[str] = []
    content_types: list[str] = []


class PromptCategoryOut(BaseModel):
    """Prompt category metadata."""

    name: str
    slug: str
    is_visible: bool = True
    is_new: bool = False


class PromptCatalogResponse(BaseModel):
    """Full prompt catalog for the picker UI."""

    prompts: list[PromptCatalogItem]
    categories: list[PromptCategoryOut]


class AnswerUpdateItem(BaseModel):
    """A single answer in the PUT /answers request."""

    position: int
    question_id: str
    response: str
