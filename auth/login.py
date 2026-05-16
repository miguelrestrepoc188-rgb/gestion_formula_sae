import streamlit as st

from auth.auth_service import sign_in
from auth.session import set_session
from database.supabase import supabase


def login_page():

    st.title("Login")

    email = st.text_input(
        "Correo",
        key="login_email"
    )

    password = st.text_input(
        "Contraseña",
        type="password",
        key="login_password"
    )

    if st.button("Ingresar"):

        try:

            response = sign_in(email, password)

            user = response.user

            profile_response = (
                supabase
                .table("profiles")
                .select("*")
                .eq("id", user.id)
                .single()
                .execute()
            )

            profile = profile_response.data

            set_session(user, profile)

            st.success("Login exitoso")
            st.rerun()

        except Exception:
            st.error("Credenciales invalidas")