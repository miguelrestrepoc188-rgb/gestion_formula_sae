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
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.profile = None