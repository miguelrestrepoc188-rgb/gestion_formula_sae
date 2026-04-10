"""
Vista de Gantt interactivo con marcado de ruta crítica.
"""
import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_CRITICAL_PATH, ESTADO_COLOR,
)


def render_gantt(df: pd.DataFrame, cpm_engine=None):
    """Renderiza Gantt interactivo con filtros y ruta crítica."""

    st.markdown("### Diagrama de Gantt")

    # ── Filtros ──
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        subs = ["Todos"] + sorted(df["subsistema"].dropna().unique().tolist())
        sel_sub = st.selectbox("Subsistema", subs, key="gantt_sub")
    with col_f2:
        if sel_sub != "Todos":
            micros = ["Todos"] + sorted(
                df[df["subsistema"] == sel_sub]["microsubsistema"].dropna().unique().tolist()
            )
        else:
            micros = ["Todos"] + sorted(df["microsubsistema"].dropna().unique().tolist())
        sel_micro = st.selectbox("Microsubsistema", micros, key="gantt_micro")
    with col_f3:
        show_critical = st.checkbox("Resaltar Ruta Crítica", value=True, key="gantt_critical")

    # ── Filtrar datos ──
    filtered = df.copy()
    if sel_sub != "Todos":
        filtered = filtered[filtered["subsistema"] == sel_sub]
    if sel_micro != "Todos":
        filtered = filtered[filtered["microsubsistema"] == sel_micro]

    # Solo actividades con fechas
    filtered = filtered[filtered["fecha_inicio"].notna() & filtered["fecha_fin"].notna()].copy()

    if filtered.empty:
        st.warning("No hay actividades con fechas completas para los filtros seleccionados.")
        return

# Obtener IDs de ruta crítica
    critical_ids = set()
    if cpm_engine and show_critical:
        critical_ids = set(cpm_engine.critical_path)

    # ── Construir datos para Gantt ──
    gantt_data = []
    for _, row in filtered.iterrows():
        is_critical = row["id"] in critical_ids
        estado = row.get("estado", "no_iniciado")

        if is_critical and show_critical:
            color = COLOR_CRITICAL_PATH
            resource = "RUTA CRÍTICA"
        else:
            color = ESTADO_COLOR.get(estado, TEXT_MUTED)
            resource = row.get("microsubsistema", "Sin asignar")

        gantt_data.append(dict(
            Task=f"{row['id']} - {str(row['actividad'])[:40]}",
            Start=row["fecha_inicio"],
            Finish=row["fecha_fin"],
            Resource=resource,
        ))

    if not gantt_data:
        st.warning("No hay datos para el Gantt.")
        return

    gantt_df = pd.DataFrame(gantt_data)

    # Color map por resource
    resources = gantt_df["Resource"].unique().tolist()
    color_map = {}
    sub_colors = {
        "Aerodinámica": LILA, "Chasis": MORADO_OSCURO, "Dirección": "#6366F1",
        "Frenos": "#EC4899", "Suspensión": "#8B5CF6", "Transmisión": "#A78BFA",
        "Batería": AMARILLO_NEON, "Potencia": AZUL_ELECTRICO, "Telemetría": "#22D3EE",
        "Shutdown System": "#F87171", "Arnés Eléctrico": "#FB923C",
        "Integración": "#34D399", "Inspección": "#A3E635",
        "Competición": "#FDE047",
        "RUTA CRÍTICA": COLOR_CRITICAL_PATH,
    }
    for r in resources:
        color_map[r] = sub_colors.get(r, TEXT_MUTED)

    colors_ordered = [color_map.get(r, TEXT_MUTED) for r in resources]

    try:
        fig = ff.create_gantt(
            gantt_df,
            colors=colors_ordered,
            index_col="Resource",
            show_colorbar=True,
            showgrid_x=True,
            showgrid_y=True,
            group_tasks=True,
            title="",
        )

        chart_height = max(400, len(gantt_data) * 22)
        x_min = gantt_df["Start"].min()
        x_max = gantt_df["Finish"].max()

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Poppins", color=BLANCO, size=10),
            height=chart_height,
            margin=dict(l=250, r=20, t=10, b=10),
            xaxis=dict(
                gridcolor=BORDER_SUBTLE, color=BLANCO,
                visible=False,
            ),
            yaxis=dict(gridcolor=BORDER_SUBTLE, color=BLANCO),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color=BLANCO)),
        )

        # Barra de meses fija (alineada con el Gantt)
        month_fig = go.Figure()
        month_fig.add_trace(go.Scatter(
            x=[x_min.to_pydatetime(), x_max.to_pydatetime()],
            y=[0, 0], mode="lines", line=dict(color="rgba(0,0,0,0)"),
            showlegend=False, hoverinfo="skip",
        ))
        month_fig.update_layout(
            height=50,
            margin=dict(l=250, r=20, t=35, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                type="date",
                dtick="M1",
                tickformat="%b %Y",
                color=BLANCO,
                gridcolor=BORDER_SUBTLE,
                side="top",
                showline=False,
            ),
            yaxis=dict(visible=False, range=[-1, 1]),
        )
        st.plotly_chart(month_fig, use_container_width=True, key="gantt_months")

        # Gantt completo en contenedor scrollable
        with st.container(height=700):
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})

    except Exception as e:
        st.error(f"Error generando Gantt: {e}")
        st.info("Intenta filtrar por un microsubsistema específico.")

    # ── Tabla resumen ──
    with st.expander("📋 Tabla de actividades filtradas"):
        display_cols = ["id", "actividad", "microsubsistema", "responsable",
                        "fecha_inicio", "fecha_fin", "duracion_semanas", "estado"]
        available = [c for c in display_cols if c in filtered.columns]
        st.dataframe(
            filtered[available].reset_index(drop=True),
            use_container_width=True,
            height=400,
        )
