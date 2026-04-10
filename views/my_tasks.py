"""
Vista de tareas personales: cada miembro ve sus actividades y entregables.
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from config import (
    ESTADO_DISPLAY, ESTADO_COLOR, ESTADO_ICON,
    LILA, AMARILLO_NEON, COLOR_DANGER, COLOR_WARNING, COLOR_OK,
    BG_CARD, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
)


def render_my_tasks(df: pd.DataFrame):
    """Renderiza la vista de tareas personales."""

    st.markdown("### Mi Panel de Tareas")

    # ── Selectores de responsable ──
    if "responsables_list" in df.columns and "responsables_grupos" in df.columns:
        # Personas individuales
        all_persons = set()
        for names in df["responsables_list"].dropna():
            all_persons.update(names)
        personas = sorted(all_persons - {""})

        # Equipos/grupos
        all_groups = set()
        for names in df["responsables_grupos"].dropna():
            all_groups.update(names)
        grupos = sorted(all_groups - {""})
    else:
        responsables_raw = sorted(df["responsable"].dropna().unique().tolist())
        personas = [r for r in responsables_raw if r not in ["Microsubsistema", "No Definido"]]
        grupos = []

    col_p, col_g = st.columns(2)
    with col_p:
        sel_persona = st.selectbox(
            "Persona",
            [""] + personas,
            key="my_tasks_persona",
            help="Selecciona tu nombre"
        )
    with col_g:
        sel_grupo = st.selectbox(
            "Equipo / Subsistema",
            [""] + grupos,
            key="my_tasks_grupo",
            help="Filtra por equipo o subsistema"
        )

    if not sel_persona and not sel_grupo:
        st.info("👆 Selecciona tu nombre o un equipo para ver las tareas asignadas.")
        return

    # ── Filtrar ──
    if "responsables_list" in df.columns:
        mask_persona = df["responsables_list"].apply(
            lambda lst: sel_persona in lst) if sel_persona else pd.Series(False, index=df.index)
        mask_grupo = df["responsables_grupos"].apply(
            lambda lst: sel_grupo in lst) if sel_grupo else pd.Series(False, index=df.index)
        my_tasks = df[mask_persona | mask_grupo].copy()
    else:
        sel_resp = sel_persona or sel_grupo
        my_tasks = df[df["responsable"] == sel_resp].copy()

    if my_tasks.empty:
        st.warning(f"No se encontraron tareas para '{sel_resp}'.")
        return

    # ── KPIs personales ──
    total = len(my_tasks)
    terminadas = len(my_tasks[my_tasks["estado"] == "terminado"])
    en_prog = len(my_tasks[my_tasks["estado"] == "en_progreso"])
    pendientes = len(my_tasks[my_tasks["estado"] == "no_iniciado"])
    avance = round(my_tasks["avance_pct"].mean(), 1) if "avance_pct" in my_tasks.columns else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Mis Tareas", total)
    c2.metric("Mi Avance", f"{avance}%")
    c3.metric("Terminadas", terminadas)
    c4.metric("Pendientes", pendientes)

    st.markdown("---")

    # ── Tareas de esta semana ──
    today = datetime.now()
    week_end = today + timedelta(days=7)

    this_week = my_tasks[
        (my_tasks["fecha_fin"].notna()) &
        (my_tasks["fecha_fin"] <= week_end) &
        (my_tasks["estado"] != "terminado")
    ].sort_values("fecha_fin")

    if not this_week.empty:
        st.markdown(f"### 🔥 Entregas próximos 7 días ({len(this_week)})")
        for _, row in this_week.iterrows():
            deadline = row["fecha_fin"]
            days_left = (deadline - today).days if pd.notna(deadline) else None
            is_overdue = days_left is not None and days_left < 0

            icon = "🔴" if is_overdue else "🟡" if days_left is not None and days_left <= 2 else "🟢"
            deadline_str = deadline.strftime("%d/%m") if pd.notna(deadline) else "Sin fecha"
            days_str = f"({abs(days_left)}d {'vencido' if is_overdue else 'restantes'})" if days_left is not None else ""

            estado_icon = ESTADO_ICON.get(row["estado"], "")

            st.markdown(
                f"**{icon} {row['id']}** — {row['actividad']}<br>"
                f"<small style='color:{TEXT_MUTED}'>"
                f"📦 {row.get('entregable', 'N/A')} · "
                f"📅 {deadline_str} {days_str} · "
                f"{estado_icon} {ESTADO_DISPLAY.get(row['estado'], row['estado'])}"
                f"</small>",
                unsafe_allow_html=True,
            )
            st.markdown("")
    else:
        st.success("✅ No tienes entregas en los próximos 7 días.")

    st.markdown("---")

    # ── Todas mis tareas agrupadas por estado ──
    st.markdown("### Todas mis tareas")

    for estado in ["en_progreso", "no_iniciado", "bloqueado", "terminado"]:
        estado_tasks = my_tasks[my_tasks["estado"] == estado]
        if estado_tasks.empty:
            continue

        display_name = ESTADO_DISPLAY.get(estado, estado)
        icon = ESTADO_ICON.get(estado, "")
        color = ESTADO_COLOR.get(estado, TEXT_MUTED)

        with st.expander(f"{icon} {display_name} ({len(estado_tasks)})", expanded=(estado == "en_progreso")):
            display_cols = ["id", "actividad", "microsubsistema", "entregable",
                            "fecha_inicio", "fecha_fin", "duracion_semanas"]
            available = [c for c in display_cols if c in estado_tasks.columns]
            st.dataframe(
                estado_tasks[available].reset_index(drop=True),
                use_container_width=True,
            )
