"""UI Components for the Hinge Client."""

from enum import IntEnum
from typing import Any, Coroutine, Type
import streamlit as st
import asyncio

from hinge_enums import (
    ChildrenStatusEnum,
    DrinkingStatusEnum,
    DrugStatusEnum,
    EducationAttainedEnum,
    MarijuanaStatusEnum,
    PoliticsEnum,
    ReligionEnum,
    SmokingStatusEnum,
)
from hinge_models import (
    AnswerContent,
    PhotoContent,
    ProfileContent,
    RecommendationSubject,
    UserProfile,
)

if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()

loop = st.session_state.event_loop
asyncio.set_event_loop(loop)


def run_async(coro: Coroutine) -> Any:
    """Run a coroutine on the app's persistent event loop."""
    return loop.run_until_complete(coro)


def _display_like_popover(
    item: PhotoContent | AnswerContent,
    profile_name: str,
    item_type: str,
    index: str,
):
    """Display the 'Like' popover."""
    item_id = item.content_id
    comment_key = f"comment_{item_type}_{item_id}_{index}"
    superlike_key = f"superlike_{item_type}_{item_id}_{index}"
    button_key = f"like_btn_{item_type}_{item_id}_{index}"

    with st.popover("Like 👍", use_container_width=True):
        comment = st.text_input("Add a comment (optional)", key=comment_key)
        use_superlike = st.checkbox("Use Superlike? ✨", key=superlike_key)

        if st.button("Send Like", key=button_key):
            try:
                with st.spinner("Sending..."):
                    run_async(
                        item.like(
                            comment=comment if comment else None,
                            use_superlike=use_superlike,
                        )
                    )
                st.toast(f"Liked {profile_name}'s {item_type}!")
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Failed to like: {e}")


def display_profile_card(  # noqa: C901
    subject: RecommendationSubject,
    profile: UserProfile,
    content: ProfileContent,
    index: str,
):
    """Render a single user profile card including all available profile data."""
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.header(f"{profile.profile.first_name}, {profile.profile.age}")
            if profile.profile.location:
                st.caption(f"📍 {profile.profile.location.name}")
        with col2:
            if st.button(
                "Skip 💀",
                key=f"skip_{subject.subject_id}_{index}",
                use_container_width=True,
            ):
                try:
                    with st.spinner("Skipping..."):
                        run_async(subject.skip())
                    st.toast(f"Skipped {profile.profile.first_name}!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to skip: {e}")

        with st.expander("View Full Profile Details 👀"):
            p_profile = profile.profile

            # FIX: New helper functions that explicitly handle data types
            def format_value(
                data: Any, enum_map: Type[IntEnum] | None = None
            ) -> str | None:
                val = data.value if hasattr(data, "value") else data
                if val is None or val == []:
                    return None

                # If an enum map is provided and the value is an integer, convert it.
                if enum_map and isinstance(val, int):
                    try:
                        val = enum_map(val)
                    except ValueError:
                        return str(val)  # Return number if not in enum

                if isinstance(val, list):
                    return ", ".join(
                        sorted(
                            [
                                v.name.replace("_", " ").title()
                                for v in val
                                if isinstance(v, IntEnum) and v.name != "UNKNOWN"
                            ]
                        )
                    )
                if isinstance(val, IntEnum) and val.name != "UNKNOWN":
                    return val.name.replace("_", " ").title()
                if isinstance(val, (int, str)) and not enum_map:
                    return str(val)
                return None

            def show_attr(
                label: str, value: Any, enum_map: Type[IntEnum] | None = None
            ):
                formatted_value = format_value(value, enum_map)
                if formatted_value:
                    st.markdown(f"**{label}:** {formatted_value}")

            c1, c2, c3 = st.columns(3)
            with c1:
                st.subheader("Vitals")
                show_attr(
                    "Height", f"{p_profile.height} cm" if p_profile.height else None
                )
                show_attr("Relationship Type", p_profile.relationship_type_ids)
                show_attr("Children", p_profile.children, enum_map=ChildrenStatusEnum)
                show_attr("Family Plans", p_profile.family_plans)
                show_attr("Ethnicities", p_profile.ethnicities)
                show_attr("Zodiac", p_profile.zodiac)
            with c2:
                st.subheader("Virtues")
                show_attr("Job Title", p_profile.job_title)
                show_attr("Work", p_profile.works)
                show_attr(
                    "Education",
                    p_profile.education_attained,
                    enum_map=EducationAttainedEnum,
                )
                show_attr("Religion", p_profile.religions, enum_map=ReligionEnum)
                show_attr("Politics", p_profile.politics, enum_map=PoliticsEnum)
                show_attr("Languages", p_profile.languages_spoken)
            with c3:
                st.subheader("Vices")
                show_attr("Drinking", p_profile.drinking, enum_map=DrinkingStatusEnum)
                show_attr("Smoking", p_profile.smoking, enum_map=SmokingStatusEnum)
                show_attr(
                    "Marijuana", p_profile.marijuana, enum_map=MarijuanaStatusEnum
                )
                show_attr("Drugs", p_profile.drugs, enum_map=DrugStatusEnum)

        st.divider()

        if content.content.photos:
            st.subheader("Photos")
            cols = st.columns(3)
            for i, photo in enumerate(content.content.photos):
                with cols[i % 3]:
                    st.image(photo.url, use_container_width=True)
                    _display_like_popover(
                        photo, profile.profile.first_name, "photo", index
                    )
            st.divider()

        # --- Prompts Section ---
        # Displays prompt answers with their own like functionality.
        if content.content.answers:
            st.subheader("Prompts")
            for answer in content.content.answers:
                with st.container(border=True):
                    st.caption(answer.question_id.prompt_text)

                    # Handle different answer types: voice, video, or text
                    if answer.type == "voice" and answer.url:
                        if answer.transcription:
                            st.markdown(f'> 🗣️ *"{answer.transcription}"*')
                        st.audio(answer.url)
                    elif answer.type == "video" and answer.url:
                        if answer.transcription:
                            st.markdown(f'> 🎞️ *"{answer.transcription}"*')
                        st.video(answer.url)
                    elif answer.response:
                        st.markdown(f'#### "{answer.response}"')

                    _display_like_popover(
                        answer, profile.profile.first_name, "answer", index
                    )
