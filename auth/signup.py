import streamlit as st

from auth.auth_service import sign_up
from database.supabase import supabase


def signup_page():

    st.title("Crear Cuenta")

    first_name = st.text_input(
        "Nombre",
        key="signup_first_name"
    )

    last_name = st.text_input(
        "Apellido",
        key="signup_last_name"
    )

    email = st.text_input(
        "Correo",
        key="signup_email"
    )

    password = st.text_input(
        "Contraseña",
        type="password",
        key="signup_password"
    )

    # Obtener subsistemas
    subsystem_response = (
        supabase
        .table("subsystems")
        .select("*")
        .execute()
    )

    subsystems = subsystem_response.data or []

    if not subsystems:
        st.error("No se pudieron cargar los subsistemas")
        st.stop()

    subsystem_names = [s["name"] for s in subsystems]

    selected_subsystem = st.selectbox(
        "Subsistema",
        subsystem_names
    )

    if st.button("Registrarse"):

        try:

            auth_response = sign_up(email, password)

            user = auth_response.user

            subsystem_id = next(
                s["id"]
                for s in subsystems
                if s["name"] == selected_subsystem
            )

            supabase.table("profiles").insert({
                "id": user.id,
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "role": "member",
                "subsystem_id": subsystem_id
            }).execute()

            st.success("Usuario creado correctamente")

            st.session_state.login_email = email
            st.session_state.auth_mode = "login"

            st.rerun()

        except Exception as e:
            st.error(str(e))