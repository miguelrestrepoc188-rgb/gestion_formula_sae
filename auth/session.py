import streamlit as st

def init_session():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "user" not in st.session_state:
        st.session_state.user = None

    if "profile" not in st.session_state:
        st.session_state.profile = None


def set_session(user, profile):
    st.session_state.authenticated = True
    st.session_state.user = user
    st.session_state.profile = profile


def clear_session():
    keys_to_clear = [
        "authenticated",
        "user",
        "profile",
        "auth_mode",
        "df",
        "report",
        "cpm_engine",
        "cpm_stats",
        "data_loaded",
        "nav",
    ]

    for key in keys_to_clear:

        if key in st.session_state:
            del st.session_state[key]

    st.session_state.auth_mode = "login"

    st.rerun()