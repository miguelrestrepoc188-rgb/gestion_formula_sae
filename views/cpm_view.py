"""
Vista de Ruta Crítica — tres niveles jerárquicos:
  - Proyecto Completo : un bloque por subsistema
  - Por Subsistema    : un bloque por microsubsistema (dentro del sub seleccionado)
  - Por Microsubsistema: actividades individuales dentro del micro seleccionado
"""
import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_CRITICAL_PATH,
)
from core.cpm_engine import CPMEngine


# ── Paleta de colores por microsubsistema / subsistema ──────────────────────
NODE_COLORS = {
    "Aerodinámica": LILA,
    "Chasis": MORADO_OSCURO,
    "Dirección": "#6366F1",
    "Frenos": "#EC4899",
    "Suspensión": "#8B5CF6",
    "Transmisión": "#A78BFA",
    "Batería": AMARILLO_NEON,
    "Potencia": AZUL_ELECTRICO,
    "Telemetría": "#22D3EE",
    "Shutdown System": "#F87171",
    "Arnés Eléctrico": "#FB923C",
    "Integración": "#34D399",
    "Inspección": "#A3E635",
    "Competición": "#FDE047",
    "DYM": LILA,
    "Electrónica": AMARILLO_NEON,
    "Documentación": "#FF6B6B",
}


# ── Helpers de agregación ────────────────────────────────────────────────────

def _build_sub_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea un DataFrame con UNA fila por subsistema.
    - fecha_inicio / fecha_fin: rango real del subsistema
    - duracion_dias: duración del rango
    - predecesores: subsistemas que contienen predecesores de actividades de este sub
    """
    df_valid = df[df["fecha_inicio"].notna() & df["fecha_fin"].notna()].copy()
    if df_valid.empty:
        return pd.DataFrame()

    id_to_sub = dict(zip(df_valid["id"].astype(str), df_valid["subsistema"]))
    rows = []

    for sub, grp in df_valid.groupby("subsistema"):
        start = grp["fecha_inicio"].min()
        end = grp["fecha_fin"].max()
        duration = max((end - start).days, 1)

        pred_subs = set()
        for _, row in grp.iterrows():
            preds = row.get("predecesores", [])
            if isinstance(preds, list):
                for pid in preds:
                    ps = id_to_sub.get(str(pid))
                    if ps and ps != sub:
                        pred_subs.add(ps)

        rows.append({
            "id": sub,
            "actividad": sub,
            "subsistema": sub,
            "microsubsistema": sub,
            "duracion_dias": duration,
            "duracion_semanas": max(1, round(duration / 7)),
            "predecesores": list(pred_subs),
            "fecha_inicio": start,
            "fecha_fin": end,
        })

    return pd.DataFrame(rows)


def _build_micro_aggregate(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea un DataFrame con UNA fila por microsubsistema.
    - fecha_inicio / fecha_fin: rango real del micro
    - predecesores: micros que contienen predecesores de actividades de este micro
    """
    df_valid = df[df["fecha_inicio"].notna() & df["fecha_fin"].notna()].copy()
    if df_valid.empty:
        return pd.DataFrame()

    id_to_micro = dict(zip(df_valid["id"].astype(str), df_valid["microsubsistema"]))
    rows = []

    for micro, grp in df_valid.groupby("microsubsistema"):
        start = grp["fecha_inicio"].min()
        end = grp["fecha_fin"].max()
        duration = max((end - start).days, 1)

        pred_micros = set()
        for _, row in grp.iterrows():
            preds = row.get("predecesores", [])
            if isinstance(preds, list):
                for pid in preds:
                    pm = id_to_micro.get(str(pid))
                    if pm and pm != micro:
                        pred_micros.add(pm)

        rows.append({
            "id": micro,
            "actividad": micro,
            "subsistema": grp["subsistema"].iloc[0],
            "microsubsistema": micro,
            "duracion_dias": duration,
            "duracion_semanas": max(1, round(duration / 7)),
            "predecesores": list(pred_micros),
            "fecha_inicio": start,
            "fecha_fin": end,
        })

    return pd.DataFrame(rows)


def _build_micro_activities(df: pd.DataFrame) -> pd.DataFrame:
    """
    Para el nivel micro: encadena cronológicamente las actividades que no
    tienen predecesores dentro del micro, para que el CPM las incluya todas.
    """
    df_valid = df[df["fecha_inicio"].notna() & df["fecha_fin"].notna()].copy()
    if df_valid.empty:
        return df_valid

    activity_ids = set(df_valid["id"].astype(str))
    df_valid = df_valid.sort_values("fecha_inicio").reset_index(drop=True)

    enriched = []
    for i, row in df_valid.iterrows():
        preds = row.get("predecesores", [])
        if not isinstance(preds, list):
            preds = []
        # Solo predecesores dentro de este micro
        internal_preds = [p for p in preds if str(p) in activity_ids]

        # Si no tiene predecesores internos y no es el primero, conectar al anterior
        if not internal_preds and i > 0:
            prev_id = str(df_valid.iloc[i - 1]["id"])
            internal_preds = [prev_id]

        row = row.copy()
        row["predecesores"] = internal_preds
        enriched.append(row)

    return pd.DataFrame(enriched)


def _get_critical_ids(df_nodes: pd.DataFrame) -> set:
    """Corre CPMEngine sobre df_nodes y devuelve IDs críticos."""
    if df_nodes.empty:
        return set()
    engine = CPMEngine()
    engine.load_from_dataframe(df_nodes)
    engine.compute()
    return set(engine.critical_path)


# ── Render del Gantt ─────────────────────────────────────────────────────────

def _render_gantt(df_critical: pd.DataFrame, label_col: str):
    """
    Dibuja un Gantt con las filas de df_critical.
    label_col: columna usada para el nombre de cada barra (e.g. 'actividad', 'microsubsistema')
    """
    if df_critical.empty:
        st.info("No hay nodos críticos con fechas para este nivel.")
        return

    df_sorted = df_critical.sort_values("fecha_inicio")
    gantt_data, resources = [], []

    for _, row in df_sorted.iterrows():
        resource = row.get("subsistema") or row.get("microsubsistema") or "Sin asignar"
        label = str(row.get(label_col, row.get("actividad", "")))[:50]
        gantt_data.append(dict(
            Task=label,
            Start=row["fecha_inicio"],
            Finish=row["fecha_fin"],
            Resource=resource,
        ))
        if resource not in resources:
            resources.append(resource)

    colors_ordered = [NODE_COLORS.get(r, COLOR_CRITICAL_PATH) for r in resources]

    try:
        fig = ff.create_gantt(
            gantt_data,
            colors=colors_ordered,
            index_col="Resource",
            show_colorbar=True,
            showgrid_x=True,
            showgrid_y=True,
            group_tasks=True,
            title="",
        )

        chart_height = max(400, len(gantt_data) * 28)
        gantt_df_temp = pd.DataFrame(gantt_data)
        x_min = gantt_df_temp["Start"].min()
        x_max = gantt_df_temp["Finish"].max()

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(family="Poppins", color=BLANCO, size=10),
            height=chart_height,
            margin=dict(l=300, r=20, t=10, b=10),
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
            margin=dict(l=300, r=20, t=35, b=0),
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
        st.plotly_chart(month_fig, use_container_width=True, key="cpm_months")

        with st.container(height=700):
            st.plotly_chart(fig, use_container_width=True, config={"scrollZoom": True})
    except Exception as e:
        st.error(f"Error generando cronograma: {e}")


# ── Vista principal ───────────────────────────────────────────────────────────

def render_cpm_view(df: pd.DataFrame, cpm_engine):
    st.markdown("### Análisis de Ruta Crítica (CPM)")

    if cpm_engine is None or not cpm_engine._computed:
        st.warning("El motor CPM no ha calculado aún.")
        return

    # Métricas globales
    total_critical = len(cpm_engine.critical_path)
    total_nodes = len(cpm_engine.nodes)
    c1, c2, c3 = st.columns(3)
    fecha_min = df["fecha_inicio"].dropna().min()
    fecha_max = df["fecha_fin"].dropna().max()
    if pd.notna(fecha_min) and pd.notna(fecha_max):
        dur_days = (fecha_max - fecha_min).days
        dur_weeks = max(1, round(dur_days / 7))
    else:
        dur_days = 0
        dur_weeks = 0
    c1.metric("Duración Proyecto", f"{dur_days}D / {dur_weeks}S")
    c2.metric("Actividades en Ruta Crítica", f"{total_critical} / {total_nodes}")
    c3.metric("% Actividades Críticas", f"{total_critical / max(total_nodes, 1) * 100:.1f}%")

    st.markdown("---")

    view_level = st.radio(
        "Nivel de visualización",
        ["Proyecto Completo", "Por Subsistema", "Por Microsubsistema"],
        horizontal=True,
        key="cpm_level",
    )

    # ── NIVEL: Proyecto Completo ─────────────────────────────────────────────
    if view_level == "Proyecto Completo":
        st.markdown("### Ruta Crítica — Subsistemas")
        st.caption("Cada barra representa un subsistema completo. Se muestran los subsistemas críticos según su cadena de fechas.")

        agg = _build_sub_aggregate(df)
        critical_ids = _get_critical_ids(agg)

        # Si no hay dependencias entre subs, todos serán críticos (corren en paralelo)
        # En ese caso mostrar todos ordenados por fecha
        critical_agg = agg[agg["id"].isin(critical_ids)].copy() if critical_ids else agg.copy()

        _render_gantt(critical_agg, label_col="actividad")

        with st.expander("📋 Detalle por subsistema"):
            display = critical_agg[["actividad", "fecha_inicio", "fecha_fin", "duracion_semanas"]].copy()
            display.columns = ["Subsistema", "Inicio", "Fin", "Duración (semanas)"]
            st.dataframe(display.reset_index(drop=True), use_container_width=True)

    # ── NIVEL: Por Subsistema ────────────────────────────────────────────────
    elif view_level == "Por Subsistema":
        subs = sorted(df["subsistema"].dropna().unique().tolist())
        sel_sub = st.selectbox("Subsistema", subs, key="cpm_sub_filter")

        st.markdown(f"### Ruta Crítica — Microsubsistemas de {sel_sub}")
        st.caption("Cada barra representa un microsubsistema completo dentro del subsistema seleccionado.")

        df_sub = df[df["subsistema"] == sel_sub]
        agg = _build_micro_aggregate(df_sub)
        critical_ids = _get_critical_ids(agg)

        critical_agg = agg[agg["id"].isin(critical_ids)].copy() if critical_ids else agg.copy()

        _render_gantt(critical_agg, label_col="actividad")

        with st.expander("📋 Detalle por microsubsistema"):
            display = critical_agg[["actividad", "fecha_inicio", "fecha_fin", "duracion_semanas"]].copy()
            display.columns = ["Microsubsistema", "Inicio", "Fin", "Duración (semanas)"]
            st.dataframe(display.reset_index(drop=True), use_container_width=True)

    # ── NIVEL: Por Microsubsistema ───────────────────────────────────────────
    else:
        micros = sorted(df["microsubsistema"].dropna().unique().tolist())
        sel_micro = st.selectbox("Microsubsistema", micros, key="cpm_micro_filter")

        st.markdown(f"### Ruta Crítica — Actividades de {sel_micro}")
        st.caption("Actividades individuales críticas dentro del microsubsistema (encadenadas cronológicamente).")

        df_micro = df[df["microsubsistema"] == sel_micro]
        df_chained = _build_micro_activities(df_micro)
        critical_ids = _get_critical_ids(df_chained)

        crit_dated = df_chained[
            df_chained["id"].astype(str).isin(critical_ids) &
            df_chained["fecha_inicio"].notna() &
            df_chained["fecha_fin"].notna()
        ].copy()

        # Para el Gantt de actividades individuales, Resource = microsubsistema
        _render_gantt(crit_dated, label_col="actividad")

        with st.expander("📋 Detalle de actividades críticas"):
            display_cols = ["id", "actividad", "responsable",
                            "fecha_inicio", "fecha_fin", "duracion_semanas", "estado"]
            available = [c for c in display_cols if c in crit_dated.columns]
            st.dataframe(crit_dated[available].reset_index(drop=True), use_container_width=True)

    # ── Estadísticas globales ────────────────────────────────────────────────
    st.markdown("---")
    st.markdown("### Estadísticas CPM por Subsistema")
    stats = cpm_engine.get_stats_by_subsystem()
    stats_rows = [
        {
            "Subsistema": sub,
            "Total Actividades": s["total"],
            "Actividades Críticas": s["critical"],
            "% Críticas": f"{s['critical'] / max(s['total'], 1) * 100:.1f}%",
            "Holgura Promedio (días)": s["avg_float"],
        }
        for sub, s in stats.items()
    ]
    if stats_rows:
        st.dataframe(pd.DataFrame(stats_rows), use_container_width=True)
