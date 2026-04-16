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
from config import GLOBAL_CSS, LILA, AMARILLO_NEON, TEXT_MUTED, BG_CARD, BLANCO, MORADO_OSCURO
from core.data_cleaner import run_pipeline, load_excel
from core.cpm_engine import CPMEngine
from views.dashboard import render_dashboard
from views.gantt import render_gantt
from views.my_tasks import render_my_tasks
from views.task_editor import render_task_editor
from views.diagnostics import render_diagnostics


# ── Inyectar CSS Kratos ──
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


# ── Estado de sesión ──
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


init_session_state()


# ── Sidebar ──
with st.sidebar:
    st.markdown(
        "<div class='kratos-header'>"
        "<div>"
        "<div class='kratos-logo'><span class='k-accent'>K</span><span class='k-rest'>RATOS</span></div>"
        "<div class='kratos-subtitle'>Project Management · FSAE EV</div>"
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # Carga de datos
    st.markdown(f"**📁 Datos del Proyecto**")

    data_source = st.radio(
        "Fuente de datos",
        ["Cargar Excel (.xlsx)", "Cargar JSON exportado"],
        key="data_source",
        label_visibility="collapsed",
    )

    if data_source == "Cargar Excel (.xlsx)":
        uploaded = st.file_uploader(
            "Sube el cronograma Excel",
            type=["xlsx"],
            key="upload_excel",
            help="El archivo Cronograma_Detallado_de_Tareas.xlsx"
        )

        if uploaded and not st.session_state.data_loaded:
            with st.spinner("Procesando Excel..."):
                # Guardar temporalmente
                temp_path = Path("data") / "temp_upload.xlsx"
                temp_path.parent.mkdir(exist_ok=True)
                temp_path.write_bytes(uploaded.getvalue())

                # Ejecutar pipeline
                df, report = run_pipeline(str(temp_path))
                st.session_state.df = df
                st.session_state.report = report
                st.session_state.data_loaded = True

                # CPM
                engine = CPMEngine()
                engine.load_from_dataframe(df)
                cpm_result = engine.compute()
                st.session_state.cpm_engine = engine
                st.session_state.cpm_stats = cpm_result

            st.success(f"✅ {len(df)} actividades cargadas")

    elif data_source == "Cargar JSON exportado":
        uploaded_json = st.file_uploader(
            "Sube un JSON previamente exportado",
            type=["json"],
            key="upload_json",
        )

        if uploaded_json and not st.session_state.data_loaded:
            import json
            try:
                data = json.loads(uploaded_json.read().decode("utf-8"))
                df = pd.DataFrame(data["activities"])
                # Convert date strings back
                for col in ["fecha_inicio", "fecha_fin"]:
                    if col in df.columns:
                        df[col] = pd.to_datetime(df[col], errors="coerce")

                st.session_state.df = df
                st.session_state.report = {"total_raw": len(df), "total_final": len(df),
                                            "fechas_corregidas": 0,
                                            "quality_summary": {}}
                st.session_state.data_loaded = True

                engine = CPMEngine()
                engine.load_from_dataframe(df)
                cpm_result = engine.compute()
                st.session_state.cpm_engine = engine
                st.session_state.cpm_stats = cpm_result

                st.success(f"✅ {len(df)} actividades importadas")
            except Exception as e:
                st.error(f"Error: {e}")

    if st.session_state.data_loaded:
        if st.button("🔄 Recargar datos", key="reload"):
            st.session_state.data_loaded = False
            st.session_state.df = None
            st.session_state.report = None
            st.session_state.cpm_engine = None
            st.session_state.cpm_stats = None
            st.rerun()

    st.markdown("---")

    # Navegación
    st.markdown(f"**🧭 Navegación**")
    page = st.radio(
        "Ir a",
        ["📊 Dashboard", "📅 Gantt", "👤 Mis Tareas",
         "✏️ Editor", "🔍 Diagnóstico"],
        key="nav",
        label_visibility="collapsed",
    )

    st.markdown("---")
    st.markdown(
        f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.7rem;'>"
        f"KRATOS PM v1.0<br>FSAE Eléctrico · EAFIT 2026"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── Contenido principal ──
if not st.session_state.data_loaded:
    # Landing page
    st.markdown(
        "<div style='text-align:center; padding:80px 20px;'>"
        "<div class='kratos-logo' style='font-size:3.5rem; margin-bottom:8px;'>"
        "<span class='k-accent'>K</span><span class='k-rest'>RATOS</span>"
        "</div>"
        f"<div style='color:{TEXT_MUTED}; font-size:1rem; letter-spacing:0.2em; "
        f"text-transform:uppercase; margin-bottom:40px;'>Project Management Platform</div>"
        f"<div style='color:{TEXT_MUTED}; font-size:0.95rem; max-width:500px; margin:0 auto;'>"
        f"Carga tu cronograma Excel desde el panel lateral para comenzar.<br><br>"
        f"El sistema limpiará los datos automáticamente, calculará la ruta crítica "
        f"y te mostrará el estado del proyecto."
        f"</div>"
        "</div>",
        unsafe_allow_html=True,
    )

else:
    df = st.session_state.df
    report = st.session_state.report
    cpm_engine = st.session_state.cpm_engine
    cpm_stats = st.session_state.cpm_stats

    if page == "📊 Dashboard":
        render_dashboard(df, cpm_stats)

    elif page == "📅 Gantt":
        render_gantt(df, cpm_engine)

    elif page == "👤 Mis Tareas":
        render_my_tasks(df)

    elif page == "✏️ Editor":
        updated_df = render_task_editor(df)
        if updated_df is not None:
            st.session_state.df = updated_df

    elif page == "🔍 Diagnóstico":
        render_diagnostics(df, report)
