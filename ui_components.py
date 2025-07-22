"""UI Components for the Hinge Client."""

from typing import Any, Coroutine
import streamlit as st
import asyncio

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
    """Display the 'Like' popover for a photo or an answer.

    This avoids code duplication and keeps the main card component clean.
    """
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
                st.cache_data.clear()  # Clear cache to refresh recommendations
                st.rerun()
            except Exception as e:
                st.error(f"Failed to like: {e}")


def display_profile_card(
    subject: RecommendationSubject,
    profile: UserProfile,
    content: ProfileContent,
    index: str,
):
    """Render single user profile card enhanced grid layout with functionality."""
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
        st.divider()

        if content.content.photos:
            st.subheader("Photos")
            cols = st.columns(3)
            for i, photo in enumerate(content.content.photos):
                with cols[i % 3]:  # Cycle through columns to create the grid
                    st.image(photo.url, use_container_width=True)
                    # Display the like popover for each photo
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
                    st.markdown(f'#### "{answer.response}"')
                    # Display the like popover for each answer
                    _display_like_popover(
                        answer, profile.profile.first_name, "answer", index
                    )
