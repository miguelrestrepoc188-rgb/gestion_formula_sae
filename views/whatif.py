"""
Vista: Simulación What-If CPM
Permite modificar duraciones de tareas y ver el impacto en la ruta crítica,
duración del proyecto y holguras antes de que ocurra el cambio real.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from copy import deepcopy

from core.cpm_engine import CPMEngine
from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_CARD, BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_OK, COLOR_WARNING, COLOR_DANGER, COLOR_CRITICAL_PATH,
)


def _hex_to_rgba(hex_color, alpha=0.5):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def _plotly_dark(fig, title="", height=350):
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


def _run_simulation(df: pd.DataFrame, modifications: dict) -> tuple[CPMEngine, dict]:
    """
    Corre CPM sobre una copia del DataFrame con las modificaciones aplicadas.
    modifications: {task_id: {"delay": days, "new_duration": days}}
    Retorna (engine_simulado, cpm_stats).
    """
    df_sim = df.copy()

    for task_id, mods in modifications.items():
        mask = df_sim["id"].astype(str) == str(task_id)
        if not mask.any():
            continue

        if "new_duration" in mods and mods["new_duration"] is not None:
            df_sim.loc[mask, "duracion_dias"] = mods["new_duration"]

        if "delay" in mods and mods["delay"] > 0:
            delay_td = pd.Timedelta(days=mods["delay"])
            df_sim.loc[mask, "fecha_inicio"] = df_sim.loc[mask, "fecha_inicio"] + delay_td
            df_sim.loc[mask, "fecha_fin"] = df_sim.loc[mask, "fecha_fin"] + delay_td
            df_sim.loc[mask, "duracion_dias"] = df_sim.loc[mask, "duracion_dias"] + mods["delay"]

    engine = CPMEngine()
    engine.load_from_dataframe(df_sim)
    stats = engine.compute()
    return engine, stats


def render_whatif(df: pd.DataFrame, cpm_engine: CPMEngine):
    """Renderiza la vista de simulación What-If."""

    st.markdown("### Simulacion What-If CPM")
    st.caption(
        "Modifica la duracion o agrega atraso a tareas y observa como impacta "
        "la ruta critica y la duracion total del proyecto."
    )

    if cpm_engine is None or not cpm_engine._computed:
        st.warning("El motor CPM no ha calculado aun. Carga un cronograma primero.")
        return

    original_duration = cpm_engine.project_duration
    original_critical = set(cpm_engine.critical_path)
    original_critical_count = len(original_critical)

    # ══════════════════════════════════════════════
    # Panel de configuración de escenario
    # ══════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Configurar Escenario")

    # Construir lista de tareas para selección
    task_options = {}
    for nid, node in cpm_engine.nodes.items():
        label = f"{nid} — {node.actividad} ({node.microsubsistema})"
        task_options[label] = nid

    # Filtros para encontrar tareas más fácilmente
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        subsistemas = sorted(set(n.subsistema for n in cpm_engine.nodes.values() if n.subsistema))
        filter_sub = st.selectbox("Filtrar por subsistema", ["Todos"] + subsistemas, key="whatif_sub")
    with col_filter2:
        if filter_sub != "Todos":
            micros = sorted(set(
                n.microsubsistema for n in cpm_engine.nodes.values()
                if n.subsistema == filter_sub and n.microsubsistema
            ))
        else:
            micros = sorted(set(n.microsubsistema for n in cpm_engine.nodes.values() if n.microsubsistema))
        filter_micro = st.selectbox("Filtrar por microsubsistema", ["Todos"] + micros, key="whatif_micro")

    # Filtrar opciones de tareas
    filtered_options = {}
    for label, nid in task_options.items():
        node = cpm_engine.nodes[nid]
        if filter_sub != "Todos" and node.subsistema != filter_sub:
            continue
        if filter_micro != "Todos" and node.microsubsistema != filter_micro:
            continue
        filtered_options[label] = nid

    if not filtered_options:
        st.info("No hay tareas con los filtros seleccionados.")
        return

    # Selección de tareas a modificar
    selected_labels = st.multiselect(
        "Selecciona las tareas a modificar",
        options=list(filtered_options.keys()),
        key="whatif_tasks",
        help="Puedes seleccionar multiples tareas para simular escenarios combinados",
    )

    if not selected_labels:
        st.info("Selecciona al menos una tarea para simular un escenario.")

        # Mostrar resumen del estado actual como referencia
        st.markdown("---")
        st.markdown("### Estado Actual del Proyecto (referencia)")
        ref1, ref2, ref3 = st.columns(3)
        ref1.metric("Duracion del Proyecto", f"{original_duration:.0f} dias")
        ref2.metric("Actividades Criticas", original_critical_count)
        ref3.metric("Total Actividades", len(cpm_engine.nodes))

        # Top 10 tareas con menor holgura (más riesgosas)
        st.markdown("#### Tareas con Menor Holgura (mayor riesgo)")
        risk_rows = []
        for nid, node in cpm_engine.nodes.items():
            risk_rows.append({
                "ID": nid,
                "Actividad": node.actividad,
                "Microsubsistema": node.microsubsistema,
                "Duracion (dias)": node.duration,
                "Holgura (dias)": node.total_float,
                "Critica": "Si" if node.is_critical else "No",
            })
        risk_df = pd.DataFrame(risk_rows).sort_values("Holgura (dias)").head(15)
        st.dataframe(risk_df, use_container_width=True, hide_index=True)
        return

    # ══════════════════════════════════════════════
    # Controles de modificación por tarea
    # ══════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### Ajustes por Tarea")

    modifications = {}

    for label in selected_labels:
        nid = filtered_options[label]
        node = cpm_engine.nodes[nid]

        st.markdown(
            f"<div style='background:{BG_CARD}; border:1px solid {BORDER_SUBTLE}; "
            f"border-radius:10px; padding:15px; margin-bottom:10px;'>"
            f"<strong style='color:{LILA}'>{nid}</strong> — {node.actividad}"
            f"<br><span style='color:{TEXT_MUTED}; font-size:0.85rem;'>"
            f"{node.microsubsistema} · Duracion actual: {node.duration:.0f} dias · "
            f"Holgura: {node.total_float:.0f} dias · "
            f"{'EN RUTA CRITICA' if node.is_critical else 'No critica'}"
            f"</span></div>",
            unsafe_allow_html=True,
        )

        col_dur, col_delay = st.columns(2)
        with col_dur:
            new_dur = st.number_input(
                f"Nueva duracion (dias)",
                min_value=1,
                value=int(node.duration),
                step=1,
                key=f"whatif_dur_{nid}",
                help=f"Duracion original: {node.duration:.0f} dias",
            )
        with col_delay:
            delay = st.number_input(
                f"Atraso adicional (dias)",
                min_value=0,
                value=0,
                step=1,
                key=f"whatif_delay_{nid}",
                help="Dias de retraso sobre la fecha de inicio planificada",
            )

        mods = {}
        if new_dur != int(node.duration):
            mods["new_duration"] = new_dur
        if delay > 0:
            mods["delay"] = delay

        if mods:
            modifications[nid] = mods

    # ══════════════════════════════════════════════
    # Ejecutar simulación
    # ══════════════════════════════════════════════
    if not modifications:
        st.info("Modifica la duracion o agrega atraso a alguna tarea para ver el impacto.")
        return

    st.markdown("---")
    st.markdown("### Resultados de la Simulacion")

    sim_engine, sim_stats = _run_simulation(df, modifications)
    sim_duration = sim_engine.project_duration
    sim_critical = set(sim_engine.critical_path)
    sim_critical_count = len(sim_critical)

    # ── KPIs comparativos ──
    delta_duration = sim_duration - original_duration
    delta_critical = sim_critical_count - original_critical_count

    k1, k2, k3, k4 = st.columns(4)
    k1.metric(
        "Duracion Original",
        f"{original_duration:.0f} dias",
    )
    k2.metric(
        "Duracion Simulada",
        f"{sim_duration:.0f} dias",
        delta=f"{delta_duration:+.0f} dias",
        delta_color="inverse" if delta_duration > 0 else "normal",
    )
    k3.metric(
        "Criticas Original",
        original_critical_count,
    )
    k4.metric(
        "Criticas Simulada",
        sim_critical_count,
        delta=f"{delta_critical:+d}",
        delta_color="inverse" if delta_critical > 0 else "normal",
    )

    # ── Alerta de impacto ──
    if delta_duration > 0:
        st.error(
            f"Este escenario **atrasa el proyecto {delta_duration:.0f} dias**. "
            f"La duracion pasa de {original_duration:.0f} a {sim_duration:.0f} dias."
        )
    elif delta_duration < 0:
        st.success(
            f"Este escenario **acorta el proyecto {abs(delta_duration):.0f} dias**. "
            f"La duracion pasa de {original_duration:.0f} a {sim_duration:.0f} dias."
        )
    else:
        st.info("Este escenario **no cambia** la duracion total del proyecto.")

    st.markdown("---")

    # ══════════════════════════════════════════════
    # Comparativa de holguras (original vs simulado)
    # ══════════════════════════════════════════════
    st.markdown("### Comparativa de Holguras")

    compare_rows = []
    for nid in cpm_engine.nodes:
        orig_node = cpm_engine.nodes[nid]
        sim_node = sim_engine.nodes.get(nid)
        if sim_node is None:
            continue

        delta_float = sim_node.total_float - orig_node.total_float
        was_critical = orig_node.is_critical
        now_critical = sim_node.is_critical

        if was_critical and not now_critical:
            status_change = "Salio de ruta critica"
        elif not was_critical and now_critical:
            status_change = "Entro a ruta critica"
        elif was_critical and now_critical:
            status_change = "Sigue critica"
        else:
            status_change = "—"

        compare_rows.append({
            "ID": nid,
            "Actividad": orig_node.actividad,
            "Micro": orig_node.microsubsistema,
            "Holgura Original": orig_node.total_float,
            "Holgura Simulada": sim_node.total_float,
            "Cambio": delta_float,
            "Cambio Ruta Critica": status_change,
        })

    compare_df = pd.DataFrame(compare_rows)

    # Mostrar primero las que cambiaron de estado, luego por cambio de holgura
    priority_order = {"Entro a ruta critica": 0, "Salio de ruta critica": 1, "Sigue critica": 2, "—": 3}
    compare_df["_priority"] = compare_df["Cambio Ruta Critica"].map(priority_order)
    compare_df = compare_df.sort_values(["_priority", "Cambio"], ascending=[True, True])
    compare_df = compare_df.drop(columns=["_priority"])

    # Filtrar solo las que tuvieron algún cambio o son críticas
    changed_df = compare_df[
        (compare_df["Cambio"].abs() > 0.5) |
        (compare_df["Cambio Ruta Critica"] != "—")
    ]

    if changed_df.empty:
        st.info("Ninguna tarea cambio de holgura o estado critico con este escenario.")
    else:
        st.dataframe(changed_df, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # Gráfico: Holguras original vs simulado (top afectadas)
    # ══════════════════════════════════════════════
    st.markdown("### Impacto en Holguras (Top 20 mas afectadas)")

    top_affected = compare_df.reindex(compare_df["Cambio"].abs().sort_values(ascending=False).index).head(20)
    top_affected = top_affected.sort_values("Cambio", ascending=True)

    if not top_affected.empty:
        fig_compare = go.Figure()

        fig_compare.add_trace(go.Bar(
            y=[f"{r['ID']} {r['Actividad'][:25]}" for _, r in top_affected.iterrows()],
            x=top_affected["Holgura Original"],
            name="Holgura Original",
            orientation="h",
            marker=dict(color=LILA),
        ))
        fig_compare.add_trace(go.Bar(
            y=[f"{r['ID']} {r['Actividad'][:25]}" for _, r in top_affected.iterrows()],
            x=top_affected["Holgura Simulada"],
            name="Holgura Simulada",
            orientation="h",
            marker=dict(color=AMARILLO_NEON),
        ))

        fig_compare = _plotly_dark(fig_compare, height=max(400, len(top_affected) * 30))
        fig_compare.update_layout(barmode="group")
        fig_compare.update_xaxes(title="Holgura (dias)")
        fig_compare.update_yaxes(title="")
        st.plotly_chart(fig_compare, use_container_width=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # Cambios en la ruta crítica
    # ══════════════════════════════════════════════
    st.markdown("### Cambios en la Ruta Critica")

    new_critical = sim_critical - original_critical
    removed_critical = original_critical - sim_critical
    still_critical = sim_critical & original_critical

    col_new, col_removed = st.columns(2)

    with col_new:
        st.markdown(f"#### Entraron a ruta critica ({len(new_critical)})")
        if new_critical:
            for nid in sorted(new_critical):
                node = sim_engine.nodes[nid]
                st.markdown(
                    f"<span style='color:{COLOR_DANGER}'>&#9679;</span> "
                    f"**{nid}** — {node.actividad} "
                    f"<span style='color:{TEXT_MUTED}'>({node.microsubsistema})</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Ninguna tarea nueva entro a la ruta critica.")

    with col_removed:
        st.markdown(f"#### Salieron de ruta critica ({len(removed_critical)})")
        if removed_critical:
            for nid in sorted(removed_critical):
                node = cpm_engine.nodes[nid]
                st.markdown(
                    f"<span style='color:{COLOR_OK}'>&#9679;</span> "
                    f"**{nid}** — {node.actividad} "
                    f"<span style='color:{TEXT_MUTED}'>({node.microsubsistema})</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("Ninguna tarea salio de la ruta critica.")

    st.markdown("---")

    # ══════════════════════════════════════════════
    # Resumen del escenario simulado
    # ══════════════════════════════════════════════
    st.markdown("### Resumen del Escenario")

    summary_lines = []
    for nid, mods in modifications.items():
        node = cpm_engine.nodes.get(nid)
        if not node:
            continue
        parts = [f"**{nid}** ({node.actividad})"]
        if "new_duration" in mods:
            parts.append(f"duracion: {node.duration:.0f} → {mods['new_duration']} dias")
        if "delay" in mods:
            parts.append(f"atraso: +{mods['delay']} dias")
        summary_lines.append(" · ".join(parts))

    for line in summary_lines:
        st.markdown(f"- {line}")

    st.markdown(
        f"\n**Resultado:** Duracion {original_duration:.0f} → {sim_duration:.0f} dias "
        f"({delta_duration:+.0f}) · "
        f"Tareas criticas {original_critical_count} → {sim_critical_count} "
        f"({delta_critical:+d})"
    )
