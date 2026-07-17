"""
Vista de tendencias: evolución histórica del avance del proyecto.
Usa los snapshots guardados en data/history.json cada vez que se carga un Excel.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from core.history import load_history
from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_CARD, BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_OK, COLOR_WARNING, COLOR_DANGER,
    ESTADO_COLOR,
)


def _plotly_dark(fig, title="", height=350):
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


def render_trends(df: pd.DataFrame):
    """Renderiza la vista de tendencias de avance."""

    st.markdown("### Tendencias de Avance")

    history = load_history()

    if len(history) < 2:
        st.info(
            "Se necesitan al menos **2 cargas de Excel** para mostrar tendencias. "
            "Cada vez que subes un cronograma se guarda un snapshot automáticamente."
        )
        if len(history) == 1:
            st.caption(f"Snapshot actual: {history[0]['timestamp']} — {history[0]['avance_pct']}% de avance")
        return

    # ── Construir DataFrame del historial ──
    hdf = pd.DataFrame(history)
    hdf["timestamp"] = pd.to_datetime(hdf["timestamp"])
    hdf = hdf.sort_values("timestamp").reset_index(drop=True)
    hdf["label"] = hdf["timestamp"].dt.strftime("%d/%m %H:%M")

    # ── KPIs de tendencia ──
    first = hdf.iloc[0]
    last = hdf.iloc[-1]
    delta_avance = round(last["avance_pct"] - first["avance_pct"], 1)
    delta_terminadas = int(last["terminadas"] - first["terminadas"])
    delta_total = int(last["total"] - first["total"])
    n_cargas = len(hdf)

    # Trabajo activo: compatibilidad con snapshots antiguos que no tienen el campo
    last_activo = last.get("trabajo_activo_pct", round(last["en_progreso"] / last["total"] * 100, 1) if last["total"] > 0 else 0.0)
    first_activo = first.get("trabajo_activo_pct", round(first["en_progreso"] / first["total"] * 100, 1) if first["total"] > 0 else 0.0)
    delta_activo = round(last_activo - first_activo, 1)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric(
        "Avance Actual",
        f"{last['avance_pct']}%",
        delta=f"{'+' if delta_avance >= 0 else ''}{delta_avance}pp desde primera carga",
        delta_color="normal" if delta_avance >= 0 else "inverse",
    )
    c2.metric(
        "Trabajo Activo",
        f"{last_activo}%",
        delta=f"{'+' if delta_activo >= 0 else ''}{delta_activo}pp",
        delta_color="normal" if delta_activo >= 0 else "inverse",
    )
    c3.metric(
        "Tareas Terminadas",
        int(last["terminadas"]),
        delta=f"+{delta_terminadas}" if delta_terminadas >= 0 else str(delta_terminadas),
    )
    c4.metric(
        "Actividades Totales",
        int(last["total"]),
        delta=f"+{delta_total}" if delta_total >= 0 else str(delta_total),
        delta_color="off",
    )
    c5.metric("Cargas Registradas", n_cargas)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 1. Curva de avance global (%)
    # ══════════════════════════════════════════════
    st.markdown("### Curva de Avance Global")

    # Calcular trabajo_activo_pct para snapshots antiguos
    if "trabajo_activo_pct" not in hdf.columns:
        hdf["trabajo_activo_pct"] = (hdf["en_progreso"] / hdf["total"] * 100).round(1)
    else:
        hdf["trabajo_activo_pct"] = hdf.apply(
            lambda r: r["trabajo_activo_pct"] if pd.notna(r.get("trabajo_activo_pct")) else round(r["en_progreso"] / r["total"] * 100, 1) if r["total"] > 0 else 0.0,
            axis=1,
        )

    fig_avance = go.Figure()
    fig_avance.add_trace(go.Scatter(
        x=hdf["timestamp"],
        y=hdf["avance_pct"],
        mode="lines+markers",
        name="Avance (terminadas)",
        line=dict(color=LILA, width=3),
        marker=dict(size=8, color=AMARILLO_NEON, line=dict(color=LILA, width=2)),
        hovertemplate="<b>%{x|%d/%m/%Y %H:%M}</b><br>Avance: %{y:.1f}%<extra></extra>",
        fill="tozeroy",
        fillcolor="rgba(158,122,225,0.08)",
    ))
    fig_avance.add_trace(go.Scatter(
        x=hdf["timestamp"],
        y=hdf["trabajo_activo_pct"],
        mode="lines+markers",
        name="Trabajo activo (en progreso)",
        line=dict(color=AZUL_ELECTRICO, width=2, dash="dot"),
        marker=dict(size=6, color=AZUL_ELECTRICO),
        hovertemplate="<b>%{x|%d/%m/%Y %H:%M}</b><br>Trabajo activo: %{y:.1f}%<extra></extra>",
    ))

    # Línea de meta 100%
    fig_avance.add_hline(
        y=100, line=dict(color=AMARILLO_NEON, width=1, dash="dash"),
        annotation_text="Meta 100%",
        annotation_font=dict(color=AMARILLO_NEON, size=11),
    )

    fig_avance = _plotly_dark(fig_avance, height=350)
    fig_avance.update_yaxes(title="Porcentaje (%)", range=[0, 110])
    fig_avance.update_xaxes(title="Fecha de carga", tickformat="%d/%m/%Y")
    st.plotly_chart(fig_avance, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 2. Evolución de tareas por estado (stacked area)
    # ══════════════════════════════════════════════
    st.markdown("### Evolución de Tareas por Estado")

    fig_estados = go.Figure()

    def _hex_to_rgba(hex_color, alpha=0.5):
        """Convierte un color hex (#RRGGBB) a rgba()."""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    estado_series = [
        ("terminadas", "Terminadas", COLOR_OK),
        ("en_progreso", "En Progreso", AZUL_ELECTRICO),
        ("no_iniciadas", "No Iniciadas", TEXT_MUTED),
        ("bloqueadas", "Bloqueadas", COLOR_DANGER),
    ]

    for col, name, color in estado_series:
        if col in hdf.columns:
            fig_estados.add_trace(go.Scatter(
                x=hdf["timestamp"],
                y=hdf[col],
                mode="lines",
                name=name,
                line=dict(width=0.5, color=color),
                stackgroup="one",
                fillcolor=_hex_to_rgba(color, 0.5),
                hovertemplate=f"<b>{name}</b>: %{{y}}<extra></extra>",
            ))

    fig_estados = _plotly_dark(fig_estados, height=400)
    fig_estados.update_yaxes(title="Cantidad de tareas")
    fig_estados.update_xaxes(title="Fecha de carga", tickformat="%d/%m/%Y")
    st.plotly_chart(fig_estados, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 3. Velocidad de avance entre cargas
    # ══════════════════════════════════════════════
    st.markdown("### Velocidad de Avance entre Cargas")

    if len(hdf) >= 2:
        hdf["delta_avance"] = hdf["avance_pct"].diff()
        hdf["delta_terminadas"] = hdf["terminadas"].diff()
        hdf_deltas = hdf.iloc[1:].copy()

        colors_bar = [
            AMARILLO_NEON if v >= 0 else COLOR_DANGER
            for v in hdf_deltas["delta_avance"]
        ]

        fig_vel = go.Figure()
        fig_vel.add_trace(go.Bar(
            x=hdf_deltas["timestamp"],
            y=hdf_deltas["delta_avance"],
            marker=dict(color=colors_bar, line=dict(width=0)),
            hovertemplate=(
                "<b>%{x|%d/%m/%Y %H:%M}</b><br>"
                "Cambio en avance: %{y:+.1f}pp<extra></extra>"
            ),
        ))
        fig_vel.add_hline(y=0, line=dict(color=TEXT_MUTED, width=1))

        fig_vel = _plotly_dark(fig_vel, height=300)
        fig_vel.update_yaxes(title="Cambio en avance (pp)")
        fig_vel.update_xaxes(title="Fecha de carga", tickformat="%d/%m/%Y")
        st.plotly_chart(fig_vel, use_container_width=True)

        # ── Resumen textual ──
        avg_delta = hdf_deltas["delta_avance"].mean()
        max_delta = hdf_deltas["delta_avance"].max()
        min_delta = hdf_deltas["delta_avance"].min()

        r1, r2, r3 = st.columns(3)
        r1.metric("Avance promedio por carga", f"{avg_delta:+.1f}pp")
        r2.metric("Mayor salto positivo", f"{max_delta:+.1f}pp")
        r3.metric("Mayor caída", f"{min_delta:+.1f}pp")

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 4. Evolución del total de actividades
    # ══════════════════════════════════════════════
    st.markdown("### Evolución del Total de Actividades")

    fig_total = go.Figure()
    fig_total.add_trace(go.Scatter(
        x=hdf["timestamp"],
        y=hdf["total"],
        mode="lines+markers",
        name="Total actividades",
        line=dict(color=AMARILLO_NEON, width=2),
        marker=dict(size=7, color=AMARILLO_NEON),
        hovertemplate="<b>%{x|%d/%m/%Y %H:%M}</b><br>Total: %{y}<extra></extra>",
    ))
    fig_total.add_trace(go.Scatter(
        x=hdf["timestamp"],
        y=hdf["terminadas"],
        mode="lines+markers",
        name="Terminadas",
        line=dict(color=COLOR_OK, width=2),
        marker=dict(size=7, color=COLOR_OK),
        hovertemplate="<b>%{x|%d/%m/%Y %H:%M}</b><br>Terminadas: %{y}<extra></extra>",
    ))

    fig_total = _plotly_dark(fig_total, height=350)
    fig_total.update_yaxes(title="Cantidad")
    fig_total.update_xaxes(title="Fecha de carga", tickformat="%d/%m/%Y")
    st.plotly_chart(fig_total, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 5. Tabla detallada del historial
    # ══════════════════════════════════════════════
    st.markdown("### Detalle del Historial")

    display_df = hdf[["timestamp", "filename", "total", "terminadas", "en_progreso", "no_iniciadas", "bloqueadas", "avance_pct", "trabajo_activo_pct"]].copy()
    display_df["timestamp"] = display_df["timestamp"].dt.strftime("%d/%m/%Y %H:%M")
    display_df.columns = [
        "Fecha", "Archivo", "Total", "Terminadas",
        "En Progreso", "No Iniciadas", "Bloqueadas", "Avance %", "Trabajo Activo %"
    ]
    st.dataframe(display_df, use_container_width=True, hide_index=True)
