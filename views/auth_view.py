import streamlit as st

from auth.login import login_page
from auth.signup import signup_page

def auth_view():

    st.title("Kratos PM")

    tab1, tab2 = st.tabs([
        "Login",
        "Registro"
    ])

    with tab1:
        login_page()

    with tab2:
        signup_page()