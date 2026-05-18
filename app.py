"""
KRATOS PM — Plataforma de Gestión de Proyecto FSAE Eléctrico
Equipo Kratos · Universidad EAFIT

Ejecutar con:
    streamlit run app.py
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# ── Configuración de página (DEBE ser lo primero) ──
st.set_page_config(
    page_title="KRATOS PM",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports del proyecto ──
from config import (
    GLOBAL_CSS,
    LILA,
    AMARILLO_NEON,
    TEXT_MUTED,
    BG_CARD,
    BLANCO,
    MORADO_OSCURO,
)

from core.data_cleaner import run_pipeline, load_excel
from core.cpm_engine import CPMEngine
from core.history import save_snapshot

from views.dashboard import render_dashboard
from views.gantt import render_gantt
from views.my_tasks import render_my_tasks
from views.task_editor import render_task_editor
from views.diagnostics import render_diagnostics
from views.cad_review import render_cad_review
from views.auth_view import auth_view

from auth.session import clear_session


# ─────────────────────────────────────────────
# CSS GLOBAL
# ─────────────────────────────────────────────
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────────
def init_session_state():

    if "df" not in st.session_state:
        st.session_state.df = None

    if "report" not in st.session_state:
        st.session_state.report = None

    if "cpm_engine" not in st.session_state:
        st.session_state.cpm_engine = None

    if "cpm_stats" not in st.session_state:
        st.session_state.cpm_stats = None

    if "data_loaded" not in st.session_state:
        st.session_state.data_loaded = False

    if "show_login" not in st.session_state:
        st.session_state.show_login = False

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "login"


init_session_state()


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:

    # ── Header ──
    st.markdown(
        "<div class='kratos-header'>"
        "<div>"
        "<div class='kratos-logo'>"
        "<span class='k-accent'>K</span>"
        "<span class='k-rest'>RATOS</span>"
        "</div>"
        "<div class='kratos-subtitle'>"
        "Project Management · FSAE EV"
        "</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("---")

    # ─────────────────────────────────────
    # USUARIO NO AUTENTICADO
    # ─────────────────────────────────────
    if not st.session_state.authenticated:

        if st.button(
            "🔐 Iniciar sesión",
            key="sidebar_login_button",
            use_container_width=True
        ):

            st.session_state.show_login = True
            st.rerun()

    # ─────────────────────────────────────
    # USUARIO AUTENTICADO
    # ─────────────────────────────────────
    else:

        st.success("✅ Sesión iniciada")

        # ── Logout ──
        if st.button(
            "🚪 Cerrar sesión",
            use_container_width=True,
            key="logout_button"
        ):

            clear_session()
            st.rerun()

        st.markdown("---")

        # ─────────────────────────────────────
        # DATOS
        # ─────────────────────────────────────
        st.markdown("**📁 Datos del Proyecto**")

        data_source = st.radio(
            "Fuente de datos",
            [
                "Cargar Excel (.xlsx)",
                "Cargar JSON exportado"
            ],
            key="data_source",
            label_visibility="collapsed",
        )

        # ── EXCEL ──
        if data_source == "Cargar Excel (.xlsx)":

            uploaded = st.file_uploader(
                "Sube el cronograma Excel",
                type=["xlsx"],
                key="upload_excel",
                help="El archivo Cronograma_Detallado_de_Tareas.xlsx"
            )

            if uploaded and not st.session_state.data_loaded:

                with st.spinner("Procesando Excel..."):

                    temp_path = Path("data") / "temp_upload.xlsx"

                    temp_path.parent.mkdir(exist_ok=True)

                    temp_path.write_bytes(
                        uploaded.getvalue()
                    )

                    # Pipeline
                    df, report = run_pipeline(
                        str(temp_path)
                    )

                    st.session_state.df = df
                    st.session_state.report = report
                    st.session_state.data_loaded = True

                    # Snapshot
                    save_snapshot(
                        df,
                        uploaded.name
                    )

                    # CPM
                    engine = CPMEngine()

                    engine.load_from_dataframe(df)

                    cpm_result = engine.compute()

                    st.session_state.cpm_engine = engine
                    st.session_state.cpm_stats = cpm_result

                st.success(
                    f"✅ {len(df)} actividades cargadas"
                )

        # ── JSON ──
        elif data_source == "Cargar JSON exportado":

            uploaded_json = st.file_uploader(
                "Sube un JSON previamente exportado",
                type=["json"],
                key="upload_json",
            )

            if uploaded_json and not st.session_state.data_loaded:

                import json

                try:

                    data = json.loads(
                        uploaded_json.read().decode("utf-8")
                    )

                    df = pd.DataFrame(
                        data["activities"]
                    )

                    # Convertir fechas
                    for col in [
                        "fecha_inicio",
                        "fecha_fin"
                    ]:

                        if col in df.columns:

                            df[col] = pd.to_datetime(
                                df[col],
                                errors="coerce"
                            )

                    st.session_state.df = df

                    st.session_state.report = {
                        "total_raw": len(df),
                        "total_final": len(df),
                        "fechas_corregidas": 0,
                        "quality_summary": {}
                    }

                    st.session_state.data_loaded = True

                    # CPM
                    engine = CPMEngine()

                    engine.load_from_dataframe(df)

                    cpm_result = engine.compute()

                    st.session_state.cpm_engine = engine
                    st.session_state.cpm_stats = cpm_result

                    st.success(
                        f"✅ {len(df)} actividades importadas"
                    )

                except Exception as e:
                    st.error(f"Error: {e}")

        # ── Reload ──
        if st.session_state.data_loaded:

            if st.button(
                "🔄 Recargar datos",
                key="reload_button"
            ):

                st.session_state.data_loaded = False
                st.session_state.df = None
                st.session_state.report = None
                st.session_state.cpm_engine = None
                st.session_state.cpm_stats = None

                st.rerun()

        st.markdown("---")

        # ─────────────────────────────────────
        # NAVEGACIÓN
        # ─────────────────────────────────────
        st.markdown("**🧭 Navegación**")

        page = st.radio(
            "Ir a",
            [
                "📊 Dashboard",
                "📅 Gantt",
                "👤 Mis Tareas",
                "✏️ Editor",
                "🔍 Diagnóstico",
                "📐 Revisión CAD"
            ],
            key="sidebar_navigation",
            label_visibility="collapsed",
        )

        st.markdown("---")

        # ── Footer ──
        st.markdown(
            f"<div style='text-align:center; "
            f"color:{TEXT_MUTED}; "
            f"font-size:0.7rem;'>"
            f"KRATOS PM v1.0<br>"
            f"FSAE Eléctrico · EAFIT 2026"
            f"</div>",
            unsafe_allow_html=True,
        )


# ─────────────────────────────────────────────
# CONTENIDO PRINCIPAL
# ─────────────────────────────────────────────

# ── Usuario NO autenticado ──
if not st.session_state.authenticated:

    if st.session_state.show_login:

        auth_view()

    else:

        st.markdown(
            "<div style='text-align:center; padding:100px 20px;'>"

            "<div class='kratos-logo' "
            "style='font-size:4rem; margin-bottom:10px;'>"

            "<span class='k-accent'>K</span>"
            "<span class='k-rest'>RATOS</span>"

            "</div>"

            f"<div style='color:{TEXT_MUTED}; "
            "font-size:1rem; "
            "letter-spacing:0.2em; "
            "text-transform:uppercase; "
            "margin-bottom:40px;'>"

            "Project Management Platform"

            "</div>"

            f"<div style='color:{TEXT_MUTED}; "
            "font-size:1rem;'>"

            "Inicia sesión para continuar"

            "</div>",

            unsafe_allow_html=True,
        )


# ── Usuario autenticado ──
else:

    # ─────────────────────────────────────
    # SIN DATOS
    # ─────────────────────────────────────
    if not st.session_state.data_loaded:

        if page == "📐 Revisión CAD":

            render_cad_review()

        else:

            st.markdown(
                "<div style='text-align:center; padding:120px 20px;'>"
                "<h1>⚡ Bienvenido a KRATOS PM</h1>"
                "<br>"
                "<p>"
                "Carga un cronograma desde el sidebar para comenzar."
                "</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    # ─────────────────────────────────────
    # CON DATOS
    # ─────────────────────────────────────
    else:

        df = st.session_state.df
        report = st.session_state.report
        cpm_engine = st.session_state.cpm_engine
        cpm_stats = st.session_state.cpm_stats

        # ── Dashboard ──
        if page == "📊 Dashboard":

            render_dashboard(
                df,
                cpm_stats
            )

        # ── Gantt ──
        elif page == "📅 Gantt":

            render_gantt(
                df,
                cpm_engine
            )

        # ── Mis tareas ──
        elif page == "👤 Mis Tareas":

            render_my_tasks(df)

        # ── Editor ──
        elif page == "✏️ Editor":

            updated_df = render_task_editor(df)

            if updated_df is not None:
                st.session_state.df = updated_df

        # ── Diagnóstico ──
        elif page == "🔍 Diagnóstico":

            render_diagnostics(
                df,
                report
            )

        # ── CAD ──
        elif page == "📐 Revisión CAD":

            render_cad_review()