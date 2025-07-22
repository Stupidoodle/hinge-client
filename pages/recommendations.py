"""Recommendation Page for the Hinge Client."""

from pydantic.json import pydantic_encoder
from typing import Any, Coroutine
import asyncio
import json
import streamlit as st

from hinge_client import HingeClient
from hinge_models import (
    RecommendationSubject,
    UserProfile,
    ProfileContent,
)
from logging_config import logger as log
from ui_components import display_profile_card

# --- Page Setup & Auth Check ---
st.set_page_config(page_title="Recommendations", page_icon="🔥", layout="wide")

# --- FIX: Create and store a single, persistent event loop for the session ---
# This ensures the HingeClient and its networking parts always use the same loop.
if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()

loop = st.session_state.event_loop
asyncio.set_event_loop(loop)


def run_async(coro: Coroutine) -> Any:
    """Run a coroutine on the app's persistent event loop."""
    return loop.run_until_complete(coro)


if not st.session_state.get("logged_in", False):
    st.warning("You must be logged in to view this page.")
    st.page_link("app.py", label="Go to Login", icon="🔒")
    st.stop()

client: HingeClient = st.session_state.client


# --- Data Fetching Logic ---
@st.cache_data(show_spinner="Fetching all profile details...")
def get_all_profile_data(_client: HingeClient) -> dict[str, dict[str, Any]]:
    """Fetch all profiles and content concurrently and return serializable dicts."""

    async def fetch_in_batches() -> dict[str, dict[str, Any]]:
        subjects = list(_client.recommendations.values())
        if not subjects:
            return {}

        subject_ids = [s.subject_id for s in subjects]
        log.info(f"Batch fetching data for {len(subject_ids)} subjects.")

        profile_task = _client.get_profiles(subject_ids)
        content_task = _client.get_profile_content(subject_ids)

        results = await asyncio.gather(
            profile_task, content_task, return_exceptions=True
        )

        profiles_result = results[0]
        content_result = results[1]

        if isinstance(profiles_result, Exception):
            log.error("Failed to fetch profiles in batch", exc_info=profiles_result)
            profiles_result = []
        if isinstance(content_result, Exception):
            log.error("Failed to fetch content in batch", exc_info=content_result)
            content_result = []

        profiles_map = {p.user_id: p for p in profiles_result}
        content_map = {c.user_id: c for c in content_result}

        final_data = {}
        for subject in subjects:
            profile_model = profiles_map.get(subject.subject_id)
            content_model = content_map.get(subject.subject_id)

            final_data[subject.subject_id] = {
                "subject": subject.model_dump(),
                "profile": profile_model.model_dump() if profile_model else None,
                "content": content_model.model_dump() if content_model else None,
            }
        json_str = json.dumps(final_data, default=pydantic_encoder)
        pickle_safe_data = json.loads(json_str)

        return pickle_safe_data

    # Use the helper function that now relies on the session's loop
    return run_async(fetch_in_batches())


# --- Sidebar ---
with st.sidebar:
    st.title("Dashboard")
    try:
        limits = run_async(client.get_like_limit())
        st.metric("Likes Left", limits.likes_left)
        st.metric("Superlikes Left", limits.super_likes_left)
    except Exception as e:
        st.error(f"Could not fetch like limits. Error: {e}")

    if st.button("Fetch New Recommendations", use_container_width=True):
        with st.spinner("Fetching..."):
            run_async(client.get_recommendations())
        st.cache_data.clear()
        st.toast("Recommendations updated!")
        st.rerun()

# --- Main Content ---
st.title("🔥 Your Recommendations")

if not client.recommendations:
    st.info(
        "No recommendations found. Click 'Fetch New Recommendations' in the sidebar."
    )

    if st.button("Ran out? ♻️ Fetch from reset pool"):
        with st.spinner("Resetting pool and fetching..."):
            run_async(client.repeat_profiles())
            run_async(client.get_recommendations())
        st.cache_data.clear()
        st.toast("Recommendation pool reset!")
        st.rerun()

else:
    profile_data_map = get_all_profile_data(client)

    if not profile_data_map:
        st.warning("Could not fetch details for any recommendations.")
    else:
        for subject_id, data in profile_data_map.items():
            if data["profile"] and data["content"] and data["subject"]:

                # --- FIX: Manually inject all required fields before validation ---

                # 1. Create a dictionary for the main subject and add the client
                subject_dict = data["subject"]
                subject_dict["client"] = client

                # 2. Grab the content dictionary
                content_dict = data["content"]

                # 3. Loop through the nested photos and answers to inject dependencies
                if content_dict and content_dict.get("content"):

                    # Inject into each photo's dictionary
                    for photo in content_dict["content"].get("photos", []):
                        photo["client"] = client
                        photo["subject"] = subject_dict

                    # Inject into each answer's dictionary
                    for answer in content_dict["content"].get("answers", []):
                        answer["client"] = client
                        answer["subject"] = subject_dict

                # 4. Now, with all dictionaries populated, validation will pass
                try:
                    subject_model = RecommendationSubject.model_validate(subject_dict)
                    profile_model = UserProfile.model_validate(data["profile"])
                    content_model = ProfileContent.model_validate(content_dict)
                except Exception as e:
                    st.error(f"Pydantic validation failed for {subject_id}: {e}")
                    continue

                # 5. Pass the validated, live models to the UI component.
                display_profile_card(
                    subject=subject_model,
                    profile=profile_model,
                    content=content_model,
                    index=subject_id,
                )
            else:
                st.error(
                    f"Could not load complete data for profile "
                    f"({subject_id}). Skipping."
                )
