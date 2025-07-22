"""UI Components for the Hinge Client."""

from typing import Any, Coroutine
import streamlit as st
import asyncio

from hinge_models import ProfileContent, RecommendationSubject, UserProfile

if "event_loop" not in st.session_state:
    st.session_state.event_loop = asyncio.new_event_loop()

loop = st.session_state.event_loop
asyncio.set_event_loop(loop)


def run_async(coro: Coroutine) -> Any:
    """Run a coroutine on the app's persistent event loop."""
    return loop.run_until_complete(coro)


def display_profile_card(
    subject: RecommendationSubject,
    profile: UserProfile,
    content: ProfileContent,
    index: str,
):
    """Render a single user profile card with actions."""
    with st.container(border=True):
        col1, col2 = st.columns([1, 4])

        with col1:
            st.subheader(f"{profile.profile.first_name}, {profile.profile.age}")
            if content.content.photos:
                st.image([p.url for p in content.content.photos], width=150)

            if st.button("Skip 💀", key=f"skip_{subject.subject_id}_{index}"):
                try:
                    with st.spinner("Skipping..."):
                        run_async(subject.skip())
                    st.toast(f"Skipped {profile.profile.first_name}!")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to skip: {e}")

        with col2:
            for answer in content.content.answers:
                with st.container(border=True):
                    st.caption(answer.question_id.prompt_text)
                    st.markdown(f"**{answer.response}**")

                    with st.popover("Like 👍", use_container_width=True):
                        comment = st.text_input(
                            "Add a comment (optional)",
                            key=f"comment_{answer.content_id}_{index}",
                        )
                        use_superlike = st.checkbox(
                            "Use Superlike? ✨",
                            key=f"superlike_{answer.content_id}_{index}",
                        )
                        if st.button(
                            "Send Like", key=f"like_btn_{answer.content_id}_{index}"
                        ):
                            try:
                                with st.spinner("Liking..."):
                                    run_async(
                                        answer.like(
                                            comment=comment or None,
                                            use_superlike=use_superlike,
                                        )
                                    )
                                st.toast(
                                    f"Liked {profile.profile.first_name}'s prompt!"
                                )
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to like: {e}")
