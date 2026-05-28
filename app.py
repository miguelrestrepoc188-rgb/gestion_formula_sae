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

    if "uploaded_file_name" not in st.session_state:
        st.session_state.uploaded_file_name = ""

    if "manual_reload_requested" not in st.session_state:
        st.session_state.manual_reload_requested = False


init_session_state()

# ─────────────────────────────────────────────
# AUTO-CARGA DEL ÚLTIMO EXCEL
# ─────────────────────────────────────────────
_last_upload = Path("data") / "last_upload.xlsx"

if (
    st.session_state.authenticated
    and not st.session_state.data_loaded
    and not st.session_state.manual_reload_requested
    and _last_upload.exists()
):
    try:
        _df, _report = run_pipeline(str(_last_upload))
        _engine = CPMEngine()
        _engine.load_from_dataframe(_df)
        _cpm_result = _engine.compute()
        st.session_state.df = _df
        st.session_state.report = _report
        st.session_state.cpm_engine = _engine
        st.session_state.cpm_stats = _cpm_result
        st.session_state.data_loaded = True
    except Exception:
        pass


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

        # ─────────────────────────────────────
        # NAVEGACIÓN
        # ─────────────────────────────────────
        st.markdown("**🧭 Navegación**")

        page = st.radio(
            "Ir a",
            [
                "🏠 Inicio",
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

            if uploaded and (
            not st.session_state.data_loaded
            or uploaded.name != st.session_state.uploaded_file_name
        ):
                with st.spinner("Procesando Excel..."):

                    last_path = Path("data") / "last_upload.xlsx"

                    last_path.parent.mkdir(exist_ok=True)

                    last_path.write_bytes(
                        uploaded.getvalue()
                    )

                    # Pipeline
                    df, report = run_pipeline(
                        str(last_path)
                    )

                    st.session_state.df = df
                    st.session_state.report = report
                    st.session_state.data_loaded = True
                    st.session_state.uploaded_file_name = uploaded.name
                    st.session_state.manual_reload_requested = False

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
                st.rerun()

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
                st.session_state.uploaded_file_name = ""
                st.session_state.manual_reload_requested = True

                st.rerun()

        st.markdown("---")

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

    profile = st.session_state.get("profile") or {}
    first_name = profile.get("first_name", "")
    welcome_name = f" {first_name}" if first_name else ""

    # ─── Inicio ───
    if page == "🏠 Inicio":

        st.markdown(
            f"<div style='text-align:center; padding:120px 20px;'>"
            f"<h1>⚡ Bienvenido{welcome_name} a KRATOS PM</h1>"
            "<br>"
            f"<p style='color:{TEXT_MUTED}; font-size:1rem;'>"
            "Selecciona una sección en el menú lateral para comenzar."
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )

    # ─── CAD (no requiere datos del Excel) ───
    elif page == "📐 Revisión CAD":

        render_cad_review()

    # ─── Páginas que requieren datos ───
    elif not st.session_state.data_loaded:

        st.markdown(
            f"<div style='text-align:center; padding:120px 20px;'>"
            f"<p style='color:{TEXT_MUTED}; font-size:1rem;'>"
            "Carga un cronograma desde el sidebar para ver esta sección."
            "</p>"
            "</div>",
            unsafe_allow_html=True,
        )

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