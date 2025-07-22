"""Utilities for the Streamlit app, including a robust async runner."""

from threading import Thread
from typing import Any, Coroutine
import asyncio
import streamlit as st


def _start_background_loop(loop: asyncio.AbstractEventLoop) -> None:
    """Start the asyncio event loop in a background thread."""
    asyncio.set_event_loop(loop)
    loop.run_forever()


def get_async_loop() -> asyncio.AbstractEventLoop:
    """Get or create the asyncio event loop for the current session.

    Starts it in a background thread if it's not already running.
    """
    if "event_loop" not in st.session_state:
        st.session_state.event_loop = asyncio.new_event_loop()
        t = Thread(
            target=_start_background_loop,
            args=(st.session_state.event_loop,),
            daemon=True,
        )
        t.start()
    return st.session_state.event_loop


def run_async(coro: Coroutine) -> Any:
    """Run a coroutine on the app's persistent and return the result."""
    loop = get_async_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result()
