import streamlit as st

from auth.login import login_page
from auth.signup import signup_page


def auth_view():

    st.title("Kratos PM")

    col1, col2 = st.columns(2)

    with col1:
        if st.button(
            "Login",
            use_container_width=True,
            type="primary"
            if st.session_state.auth_mode == "login"
            else "secondary",
            key="auth_login_tab"
        ):
            st.session_state.auth_mode = "login"
            st.rerun()

    with col2:
        if st.button(
            "Registro",
            use_container_width=True,
            type="primary"
            if st.session_state.auth_mode == "signup"
            else "secondary",
            key="auth_signup_tab"
        ):
            st.session_state.auth_mode = "signup"
            st.rerun()

    st.divider()

    if st.session_state.auth_mode == "login":
        login_page()

    else:
        signup_page()