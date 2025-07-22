"""Streamlit app for the Hinge client."""

import asyncio
import streamlit as st
import glob
import json
import time

from hinge_client import HingeClient
from hinge_error import HingeAuthError
from logging_config import logger as log

st.set_page_config(
    page_title="Unhinged",
    page_icon="💀",
    layout="wide",
)


def find_session_files():
    """Find all session files in the current directory."""
    return glob.glob("session*.json")


# State management
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "client" not in st.session_state:
    st.session_state.client = None

st.title("Welcome to the (Un)Hinge(d) Command Center 💀")

if st.session_state.logged_in:
    log.info("User already logged in, switching to recommendations page.")
    st.switch_page("pages/1_Recommendations.py")

st.header("Load Session")
session_files = find_session_files()
new_session_option = "Create New Session..."
selected_session = st.selectbox(
    "Choose an existing session or create a new one:",
    options=[new_session_option] + session_files,
)

client_initialized = False
if selected_session and selected_session != new_session_option:
    if (
        not st.session_state.client
        or st.session_state.client.session_file != selected_session
    ):
        log.info(f"Loading session from file: {selected_session}")
        with open(selected_session, "r") as f:
            log.info(f"Reading session file: {selected_session}")
            session_data = json.load(f)

        phone_number = session_data.get("phone_number")

        st.session_state.client = HingeClient(
            phone_number=phone_number, session_file=selected_session
        )
        client_initialized = True
elif selected_session == new_session_option:
    phone_number = st.text_input(
        "Enter New Phone Number to Create Session",
        placeholder="+1234567890",
    )
    if phone_number:
        if (
            not st.session_state.client
            or st.session_state.client.phone_number != phone_number
        ):
            st.session_state.client = HingeClient(phone_number=phone_number)
            client_initialized = True

client = st.session_state.client

if client and (client_initialized or st.button("Check Session / Login")):
    if asyncio.run(client.is_session_valid()):
        st.success("🎉 Valid session loaded! Redirecting...")
        st.session_state.logged_in = True
        time.sleep(1)
        st.rerun()
    else:
        st.warning("Session is invalid or expired. Please log in.")
        try:
            with st.spinner("Requesting OTP..."):
                asyncio.run(client.initiate_login())
            st.session_state.otp_requested = True
        except Exception as e:
            st.error(f"Login initiation failed: {e}")


if st.session_state.get("otp_requested", False) and client:
    with st.form("otp_form"):
        otp_code = st.text_input("Enter OTP", placeholder="123456")
        submitted = st.form_submit_button("Submit OTP")
        if submitted and otp_code:
            try:
                with st.spinner("Authenticating..."):
                    asyncio.run(client.submit_otp(otp_code.strip()))
                st.session_state.logged_in = True
                st.success("Authentication Successful! Redirecting...")
                st.rerun()
            except HingeAuthError as e:
                st.error(f"Authentication failed: {e}")
