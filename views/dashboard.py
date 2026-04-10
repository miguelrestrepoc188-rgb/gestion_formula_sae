"""
Vista principal del dashboard: resumen ejecutivo del proyecto.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_CARD, BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_OK, COLOR_WARNING, COLOR_DANGER,
    ESTADO_DISPLAY, ESTADO_COLOR, ESTADO_ICON,
)


def plotly_dark_layout(fig, title="", height=350):
    """Aplica tema Kratos a un gráfico Plotly."""
    fig.update_layout(
        title=dict(text=title, font=dict(family="Poppins", size=16, color=BLANCO)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins", color=TEXT_MUTED, size=12),
        height=height,
        margin=dict(l=20, r=20, t=50, b=20),
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color=BLANCO, size=11),
        ),
        xaxis=dict(gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE),
        yaxis=dict(gridcolor=BORDER_SUBTLE, zerolinecolor=BORDER_SUBTLE),
    )
    return fig


def render_dashboard(df: pd.DataFrame, cpm_stats: dict):
    """Renderiza el dashboard principal."""

    # ── KPIs principales ──
    total = len(df)
    terminadas = len(df[df["estado"] == "terminado"])
    en_progreso = len(df[df["estado"] == "en_progreso"])
    no_iniciadas = len(df[df["estado"] == "no_iniciado"])
    avance_global = round(df["avance_pct"].mean(), 1)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Actividades Totales", total)
    c2.metric("Avance Global", f"{avance_global}%")
    c3.metric("Terminadas", terminadas, delta=f"{round(terminadas/total*100,1)}%")
    c4.metric("En Progreso", en_progreso)

    st.markdown("---")

    # ── Dos columnas: avance por subsistema + estados ──
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("### Avance por Microsubsistema")
        micro_progress = (
            df.groupby(["subsistema", "microsubsistema"])["avance_pct"]
            .mean()
            .reset_index()
            .sort_values("avance_pct", ascending=True)
        )

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            y=micro_progress["microsubsistema"],
            x=micro_progress["avance_pct"],
            orientation="h",
            marker=dict(
                color=micro_progress["avance_pct"],
                colorscale=[[0, MORADO_OSCURO], [0.5, LILA], [1, AMARILLO_NEON]],
                line=dict(width=0),
            ),
            text=micro_progress["avance_pct"].apply(lambda x: f"{x:.0f}%"),
            textposition="outside",
            textfont=dict(color=BLANCO, size=11),
        ))
        fig_bar = plotly_dark_layout(fig_bar, height=max(300, len(micro_progress) * 35))
        fig_bar.update_xaxes(range=[0, 105], title="Avance (%)")
        fig_bar.update_yaxes(title="")
        st.plotly_chart(fig_bar, use_container_width=True)

    with col_right:
        st.markdown("### Distribución de Estados")
        estado_counts = df["estado"].value_counts()
        colors_map = [ESTADO_COLOR.get(e, TEXT_MUTED) for e in estado_counts.index]
        labels_map = [f"{ESTADO_ICON.get(e, '')} {ESTADO_DISPLAY.get(e, e)}" for e in estado_counts.index]

        fig_pie = go.Figure(data=[go.Pie(
            labels=labels_map,
            values=estado_counts.values,
            hole=0.55,
            marker=dict(colors=colors_map, line=dict(color=BG_PRIMARY, width=2)),
            textfont=dict(color=BLANCO, size=12),
            textinfo="percent+label",
        )])
        fig_pie = plotly_dark_layout(fig_pie, height=350)
        st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # ── CPM Stats ──
    if cpm_stats and "error" not in cpm_stats:
        st.markdown("### Métricas de Ruta Crítica")
        cc1, cc2, cc3 = st.columns(3)
        fecha_min = df["fecha_inicio"].dropna().min()
        fecha_max = df["fecha_fin"].dropna().max()
        if pd.notna(fecha_min) and pd.notna(fecha_max):
            dur_days = (fecha_max - fecha_min).days
            dur_weeks = max(1, round(dur_days / 7))
        else:
            dur_days = 0
            dur_weeks = 0
        cc1.metric("Duración Proyecto", f"{dur_days}D / {dur_weeks}S")
        cc2.metric("Actividades Críticas", cpm_stats.get("critical_activities", 0))
        cc3.metric("Con Predecesores", cpm_stats.get("activities_with_predecessors", 0))
    elif cpm_stats and "error" in cpm_stats:
        st.warning(f"⚠️ CPM: {cpm_stats['error']}")

    st.markdown("---")

    # ── Data Quality ──
    st.markdown("### Calidad de Datos")
    if "quality_score" in df.columns:
        avg_quality = df["quality_score"].mean()
        quality_color = COLOR_OK if avg_quality > 70 else COLOR_WARNING if avg_quality > 40 else COLOR_DANGER

        qc1, qc2, qc3, qc4 = st.columns(4)
        sin_dur = len(df[df["quality_issues"].apply(lambda x: "sin_duracion" in x if isinstance(x, list) else False)])
        sin_resp = len(df[df["quality_issues"].apply(lambda x: "sin_responsable" in x if isinstance(x, list) else False)])
        sin_pred = len(df[df["quality_issues"].apply(lambda x: "sin_predecesores" in x if isinstance(x, list) else False)])
        sin_fecha = len(df[df["quality_issues"].apply(lambda x: "sin_fecha_inicio" in x if isinstance(x, list) else False)])

        qc1.metric("Score Calidad Promedio", f"{avg_quality:.0f}/100")
        qc2.metric("Sin Duración", sin_dur)
        qc3.metric("Sin Responsable", sin_resp)
        qc4.metric("Sin Predecesores", sin_pred)

    # ── Timeline overview ──
    st.markdown("---")
    st.markdown("### Timeline de Actividades")
    df_with_dates = df[df["fecha_inicio"].notna() & df["fecha_fin"].notna()].copy()

    if not df_with_dates.empty:
        sub_colors = {"DYM": LILA, "Electrónica": AMARILLO_NEON,
                      "Integración": AZUL_ELECTRICO, "Documentación": "#FF6B6B"}

        fig_timeline = go.Figure()
        for sub in df_with_dates["subsistema"].unique():
            sub_df = df_with_dates[df_with_dates["subsistema"] == sub]
            color = sub_colors.get(sub, TEXT_MUTED)
            fig_timeline.add_trace(go.Scatter(
                x=sub_df["fecha_inicio"],
                y=sub_df["microsubsistema"],
                mode="markers",
                name=sub,
                marker=dict(size=8, color=color, opacity=0.7),
                text=sub_df["actividad"],
                hovertemplate="<b>%{text}</b><br>Inicio: %{x}<extra></extra>",
            ))

        fig_timeline = plotly_dark_layout(fig_timeline, "Dispersión temporal por microsubsistema", 400)
        fig_timeline.update_xaxes(title="Fecha")
        st.plotly_chart(fig_timeline, use_container_width=True)
    else:
        st.warning("No hay actividades con fechas completas para mostrar timeline.")
