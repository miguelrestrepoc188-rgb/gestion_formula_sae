"""
Vista: Countdown a Competencia + Avance vs Tiempo
Muestra cuánto falta para la competencia FSAE, deadlines intermedios,
y compara el avance real contra el tiempo consumido por subsistema.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import date

from config import (
    LILA, AMARILLO_NEON, AZUL_ELECTRICO, MORADO_OSCURO,
    BG_CARD, BG_PRIMARY, BORDER_SUBTLE, TEXT_MUTED, BLANCO,
    COLOR_OK, COLOR_WARNING, COLOR_DANGER,
)


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


def _hex_to_rgba(hex_color, alpha=0.5):
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


# ── Deadlines FSAE (editables por el usuario en la UI) ──
DEFAULT_DEADLINES = [
    {"nombre": "Fin Diseno a Detalle", "fecha": "2026-03-01", "fase": "Diseno"},
    {"nombre": "Inicio Manufactura", "fecha": "2026-03-15", "fase": "Manufactura"},
    {"nombre": "Fin Manufactura", "fecha": "2026-07-01", "fase": "Manufactura"},
    {"nombre": "Inicio Pruebas", "fecha": "2026-07-15", "fase": "Pruebas"},
    {"nombre": "Entrega Design Report", "fecha": "2026-08-01", "fase": "Documentacion"},
    {"nombre": "Entrega Cost Report", "fecha": "2026-08-01", "fase": "Documentacion"},
    {"nombre": "Entrega Business Plan", "fecha": "2026-08-15", "fase": "Documentacion"},
    {"nombre": "Technical Inspection", "fecha": "2026-09-01", "fase": "Competencia"},
    {"nombre": "Competencia FSAE", "fecha": "2026-10-01", "fase": "Competencia"},
]


def render_countdown(df: pd.DataFrame):
    """Renderiza la vista de countdown y avance vs tiempo."""

    st.markdown("### Countdown a Competencia FSAE")

    today = date.today()
    today_ts = pd.Timestamp(today)

    # ══════════════════════════════════════════════
    # 1. Configuración de fecha de competencia
    # ══════════════════════════════════════════════
    with st.expander("Configurar fechas clave", expanded=False):
        st.caption(
            "Ajusta las fechas segun el calendario real de tu competencia. "
            "Los cambios se aplican solo durante esta sesion."
        )

        if "countdown_deadlines" not in st.session_state:
            st.session_state.countdown_deadlines = [d.copy() for d in DEFAULT_DEADLINES]

        deadlines = st.session_state.countdown_deadlines

        for i, dl in enumerate(deadlines):
            col_name, col_date, col_fase = st.columns([3, 2, 2])
            with col_name:
                deadlines[i]["nombre"] = st.text_input(
                    "Evento", value=dl["nombre"], key=f"cd_name_{i}",
                    label_visibility="collapsed",
                )
            with col_date:
                deadlines[i]["fecha"] = str(st.date_input(
                    "Fecha", value=pd.to_datetime(dl["fecha"]).date(), key=f"cd_date_{i}",
                    label_visibility="collapsed",
                ))
            with col_fase:
                deadlines[i]["fase"] = st.selectbox(
                    "Fase", ["Diseno", "Manufactura", "Pruebas", "Documentacion", "Competencia"],
                    index=["Diseno", "Manufactura", "Pruebas", "Documentacion", "Competencia"].index(dl["fase"]),
                    key=f"cd_fase_{i}",
                    label_visibility="collapsed",
                )

    deadlines = st.session_state.get("countdown_deadlines", DEFAULT_DEADLINES)

    # Encontrar la fecha de competencia (último deadline tipo "Competencia")
    comp_deadlines = [d for d in deadlines if d["fase"] == "Competencia"]
    if comp_deadlines:
        competition_date = pd.to_datetime(comp_deadlines[-1]["fecha"]).date()
        competition_name = comp_deadlines[-1]["nombre"]
    else:
        competition_date = pd.to_datetime(DEFAULT_DEADLINES[-1]["fecha"]).date()
        competition_name = DEFAULT_DEADLINES[-1]["nombre"]

    days_to_competition = (competition_date - today).days

    # ══════════════════════════════════════════════
    # 2. Countdown principal
    # ══════════════════════════════════════════════
    if days_to_competition > 0:
        weeks = days_to_competition // 7
        remaining_days_mod = days_to_competition % 7

        # Countdown grande con HTML
        if days_to_competition > 90:
            count_color = AMARILLO_NEON
        elif days_to_competition > 30:
            count_color = COLOR_WARNING
        else:
            count_color = COLOR_DANGER

        st.markdown(
            f"<div style='text-align:center; padding:30px 0;'>"
            f"<div style='font-size:4.5rem; font-weight:900; color:{count_color}; "
            f"font-family:Poppins; line-height:1;'>{days_to_competition}</div>"
            f"<div style='font-size:1.2rem; color:{TEXT_MUTED}; letter-spacing:0.15em; "
            f"text-transform:uppercase; margin-top:5px;'>dias para {competition_name}</div>"
            f"<div style='font-size:1rem; color:{BLANCO}; margin-top:10px;'>"
            f"{weeks} semanas y {remaining_days_mod} dias · "
            f"{competition_date.strftime('%d/%m/%Y')}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    elif days_to_competition == 0:
        st.markdown(
            f"<div style='text-align:center; padding:30px 0;'>"
            f"<div style='font-size:3rem; font-weight:900; color:{AMARILLO_NEON}; "
            f"font-family:Poppins;'>HOY ES EL DIA</div>"
            f"<div style='font-size:1.2rem; color:{TEXT_MUTED};'>{competition_name}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f"<div style='text-align:center; padding:30px 0;'>"
            f"<div style='font-size:3rem; font-weight:900; color:{COLOR_OK}; "
            f"font-family:Poppins;'>COMPETENCIA FINALIZADA</div>"
            f"<div style='font-size:1rem; color:{TEXT_MUTED};'>"
            f"{competition_name} fue hace {abs(days_to_competition)} dias</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 3. Avance global vs tiempo consumido
    # ══════════════════════════════════════════════
    st.markdown("### Avance vs Tiempo")

    total = len(df)
    terminadas = (df["estado"] == "terminado").sum()
    avance_global = round(terminadas / total * 100, 1) if total > 0 else 0.0

    # Calcular tiempo consumido desde el inicio del proyecto hasta la competencia
    all_dates = pd.concat([df["fecha_inicio"].dropna(), df["fecha_fin"].dropna()])
    if not all_dates.empty:
        mode_year = all_dates.dt.year.mode().iloc[0]
        valid_starts = df["fecha_inicio"].dropna()
        valid_starts = valid_starts[valid_starts.dt.year == mode_year]
        project_start = valid_starts.min() if not valid_starts.empty else pd.NaT
    else:
        project_start = pd.NaT

    if pd.notna(project_start) and days_to_competition != 0:
        total_project_days = (competition_date - project_start.date()).days
        elapsed_days = (today - project_start.date()).days
        pct_tiempo = min(100.0, round(elapsed_days / max(total_project_days, 1) * 100, 1))
    else:
        total_project_days = 0
        elapsed_days = 0
        pct_tiempo = 0.0

    # Gauge doble: avance vs tiempo
    fig_gauge = go.Figure()

    # Gauge de tiempo consumido
    fig_gauge.add_trace(go.Indicator(
        mode="gauge+number",
        value=pct_tiempo,
        title={"text": "Tiempo Consumido", "font": {"size": 16, "color": BLANCO}},
        number={"suffix": "%", "font": {"size": 28, "color": BLANCO}},
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(color=TEXT_MUTED)),
            bar=dict(color=LILA),
            bgcolor=BORDER_SUBTLE,
            steps=[
                {"range": [0, 50], "color": _hex_to_rgba(LILA, 0.1)},
                {"range": [50, 75], "color": _hex_to_rgba(COLOR_WARNING, 0.1)},
                {"range": [75, 100], "color": _hex_to_rgba(COLOR_DANGER, 0.1)},
            ],
        ),
        domain={"x": [0, 0.45], "y": [0, 1]},
    ))

    # Gauge de avance real
    fig_gauge.add_trace(go.Indicator(
        mode="gauge+number",
        value=avance_global,
        title={"text": "Avance Real", "font": {"size": 16, "color": BLANCO}},
        number={"suffix": "%", "font": {"size": 28, "color": BLANCO}},
        gauge=dict(
            axis=dict(range=[0, 100], tickfont=dict(color=TEXT_MUTED)),
            bar=dict(color=AMARILLO_NEON),
            bgcolor=BORDER_SUBTLE,
            steps=[
                {"range": [0, 33], "color": _hex_to_rgba(COLOR_DANGER, 0.1)},
                {"range": [33, 66], "color": _hex_to_rgba(COLOR_WARNING, 0.1)},
                {"range": [66, 100], "color": _hex_to_rgba(COLOR_OK, 0.1)},
            ],
        ),
        domain={"x": [0.55, 1], "y": [0, 1]},
    ))

    fig_gauge.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Poppins", color=TEXT_MUTED),
        height=280,
        margin=dict(l=30, r=30, t=40, b=10),
    )
    st.plotly_chart(fig_gauge, use_container_width=True)

    # Diagnóstico de salud
    diff_pp = round(avance_global - pct_tiempo, 1)
    if diff_pp >= 5:
        st.success(
            f"El proyecto va **{diff_pp}pp adelantado** respecto al tiempo. "
            f"Avance: {avance_global}% · Tiempo consumido: {pct_tiempo}%"
        )
    elif diff_pp >= -5:
        st.info(
            f"El proyecto va **a ritmo** con el tiempo ({diff_pp:+.1f}pp). "
            f"Avance: {avance_global}% · Tiempo consumido: {pct_tiempo}%"
        )
    elif diff_pp >= -20:
        st.warning(
            f"El proyecto va **{abs(diff_pp)}pp atrasado** respecto al tiempo. "
            f"Avance: {avance_global}% · Tiempo consumido: {pct_tiempo}% — se necesita acelerar."
        )
    else:
        st.error(
            f"El proyecto va **{abs(diff_pp)}pp atrasado** respecto al tiempo. "
            f"Avance: {avance_global}% · Tiempo consumido: {pct_tiempo}% — riesgo critico."
        )

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 4. Timeline de deadlines
    # ══════════════════════════════════════════════
    st.markdown("### Timeline de Deadlines")

    fase_colors = {
        "Diseno": LILA,
        "Manufactura": AZUL_ELECTRICO,
        "Pruebas": AMARILLO_NEON,
        "Documentacion": COLOR_WARNING,
        "Competencia": COLOR_DANGER,
    }

    dl_sorted = sorted(deadlines, key=lambda d: d["fecha"])

    # Gráfico timeline
    fig_timeline = go.Figure()

    for dl in dl_sorted:
        dl_date = pd.to_datetime(dl["fecha"])
        dl_days = (dl_date.date() - today).days
        color = fase_colors.get(dl["fase"], TEXT_MUTED)
        passed = dl_days < 0

        fig_timeline.add_trace(go.Scatter(
            x=[dl_date],
            y=[dl["fase"]],
            mode="markers+text",
            marker=dict(
                size=16,
                color=color if not passed else TEXT_MUTED,
                symbol="diamond" if not passed else "diamond-open",
                line=dict(width=2, color=color),
            ),
            text=[dl["nombre"]],
            textposition="top center",
            textfont=dict(
                size=10,
                color=BLANCO if not passed else TEXT_MUTED,
            ),
            hovertemplate=(
                f"<b>{dl['nombre']}</b><br>"
                f"Fecha: {dl_date.strftime('%d/%m/%Y')}<br>"
                f"{'Hace ' + str(abs(dl_days)) + ' dias' if passed else 'En ' + str(dl_days) + ' dias'}"
                f"<extra></extra>"
            ),
            showlegend=False,
        ))

    # Línea de HOY
    fig_timeline.add_vline(
        x=today_ts.value // 10**6,
        line=dict(color=AMARILLO_NEON, width=2, dash="dash"),
        annotation_text="HOY",
        annotation_font=dict(color=AMARILLO_NEON, size=12),
    )

    fig_timeline = _plotly_dark(fig_timeline, height=300)
    fig_timeline.update_xaxes(title="", tickformat="%b %Y")
    fig_timeline.update_yaxes(title="")
    st.plotly_chart(fig_timeline, use_container_width=True)

    # Tabla de deadlines con estado
    dl_rows = []
    for dl in dl_sorted:
        dl_date = pd.to_datetime(dl["fecha"]).date()
        dl_days = (dl_date - today).days
        if dl_days < 0:
            estado = "Vencido"
        elif dl_days == 0:
            estado = "Hoy"
        elif dl_days <= 14:
            estado = "Proximo"
        else:
            estado = "Pendiente"

        dl_rows.append({
            "Evento": dl["nombre"],
            "Fecha": dl_date.strftime("%d/%m/%Y"),
            "Fase": dl["fase"],
            "Dias Restantes": dl_days if dl_days >= 0 else f"Hace {abs(dl_days)} dias",
            "Estado": estado,
        })

    st.dataframe(pd.DataFrame(dl_rows), use_container_width=True, hide_index=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 5. Avance vs Tiempo por Subsistema
    # ══════════════════════════════════════════════
    st.markdown("### Avance vs Tiempo por Subsistema")

    sub_colors = {"DYM": LILA, "Electr\u00f3nica": AMARILLO_NEON}

    sub_data = []
    for sub, grp in df.groupby("subsistema"):
        sub_total = len(grp)
        sub_terminadas = (grp["estado"] == "terminado").sum()
        sub_avance = round(sub_terminadas / sub_total * 100, 1) if sub_total > 0 else 0.0

        # Tiempo consumido del subsistema: desde su primera fecha hasta hoy / hasta su última fecha
        sub_starts = grp["fecha_inicio"].dropna()
        sub_ends = grp["fecha_fin"].dropna()
        if not sub_starts.empty and not sub_ends.empty:
            sub_start = sub_starts.min()
            sub_end = sub_ends.max()
            sub_total_days = max((sub_end - sub_start).days, 1)
            sub_elapsed = max((today_ts - sub_start).days, 0)
            sub_pct_tiempo = min(100.0, round(sub_elapsed / sub_total_days * 100, 1))
        else:
            sub_pct_tiempo = 0.0

        diff = round(sub_avance - sub_pct_tiempo, 1)
        if diff >= 0:
            salud = "Adelantado"
        elif diff >= -15:
            salud = "En riesgo"
        else:
            salud = "Critico"

        sub_data.append({
            "subsistema": sub,
            "avance": sub_avance,
            "tiempo": sub_pct_tiempo,
            "diff": diff,
            "salud": salud,
            "terminadas": int(sub_terminadas),
            "total": sub_total,
        })

    if sub_data:
        # Gráfico de barras agrupadas: avance vs tiempo por subsistema
        sub_df = pd.DataFrame(sub_data)

        fig_sub = go.Figure()
        fig_sub.add_trace(go.Bar(
            x=sub_df["subsistema"],
            y=sub_df["tiempo"],
            name="Tiempo consumido",
            marker=dict(color=LILA),
        ))
        fig_sub.add_trace(go.Bar(
            x=sub_df["subsistema"],
            y=sub_df["avance"],
            name="Avance real",
            marker=dict(color=AMARILLO_NEON),
        ))

        # Línea de referencia ideal (avance = tiempo)
        fig_sub.add_hline(
            y=pct_tiempo,
            line=dict(color=TEXT_MUTED, width=1, dash="dot"),
            annotation_text=f"Ritmo ideal ({pct_tiempo}%)",
            annotation_font=dict(color=TEXT_MUTED, size=10),
        )

        fig_sub = _plotly_dark(fig_sub, height=350)
        fig_sub.update_layout(barmode="group")
        fig_sub.update_yaxes(title="Porcentaje (%)", range=[0, 110])
        fig_sub.update_xaxes(title="")
        st.plotly_chart(fig_sub, use_container_width=True)

        # Tabla resumen
        display_sub = sub_df[["subsistema", "avance", "tiempo", "diff", "terminadas", "total", "salud"]].copy()
        display_sub.columns = ["Subsistema", "Avance %", "Tiempo %", "Diferencia (pp)", "Terminadas", "Total", "Salud"]
        st.dataframe(display_sub, use_container_width=True, hide_index=True)

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 6. Avance vs Tiempo por Microsubsistema
    # ══════════════════════════════════════════════
    st.markdown("### Avance vs Tiempo por Microsubsistema")

    micro_data = []
    for (sub, micro), grp in df.groupby(["subsistema", "microsubsistema"]):
        m_total = len(grp)
        m_terminadas = (grp["estado"] == "terminado").sum()
        m_avance = round(m_terminadas / m_total * 100, 1) if m_total > 0 else 0.0

        m_starts = grp["fecha_inicio"].dropna()
        m_ends = grp["fecha_fin"].dropna()
        if not m_starts.empty and not m_ends.empty:
            m_start = m_starts.min()
            m_end = m_ends.max()
            m_total_days = max((m_end - m_start).days, 1)
            m_elapsed = max((today_ts - m_start).days, 0)
            m_pct_tiempo = min(100.0, round(m_elapsed / m_total_days * 100, 1))
        else:
            m_pct_tiempo = 0.0

        m_diff = round(m_avance - m_pct_tiempo, 1)

        micro_data.append({
            "subsistema": sub,
            "micro": micro,
            "avance": m_avance,
            "tiempo": m_pct_tiempo,
            "diff": m_diff,
            "terminadas": int(m_terminadas),
            "total": m_total,
        })

    if micro_data:
        micro_df = pd.DataFrame(micro_data).sort_values("diff", ascending=True)

        # Gráfico: diferencia avance - tiempo (barras horizontales)
        colors_diff = [
            COLOR_OK if d >= 0 else COLOR_WARNING if d >= -15 else COLOR_DANGER
            for d in micro_df["diff"]
        ]

        fig_micro = go.Figure()
        fig_micro.add_trace(go.Bar(
            y=micro_df["micro"],
            x=micro_df["diff"],
            orientation="h",
            marker=dict(color=colors_diff, line=dict(width=0)),
            text=micro_df.apply(
                lambda r: f"{r['diff']:+.0f}pp ({int(r['terminadas'])}/{int(r['total'])})", axis=1
            ),
            textposition="outside",
            textfont=dict(color=BLANCO, size=11),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Avance - Tiempo: %{x:+.1f}pp<extra></extra>"
            ),
        ))

        fig_micro.add_vline(x=0, line=dict(color=TEXT_MUTED, width=1))

        fig_micro = _plotly_dark(fig_micro, height=max(300, len(micro_df) * 35))
        fig_micro.update_xaxes(title="Diferencia Avance - Tiempo (pp)")
        fig_micro.update_yaxes(title="")
        st.plotly_chart(fig_micro, use_container_width=True)

        st.caption(
            "Valores positivos (verde) = el microsubsistema va adelantado. "
            "Valores negativos (rojo) = va atrasado respecto a su ventana de tiempo."
        )

    st.markdown("---")

    # ══════════════════════════════════════════════
    # 7. Velocidad necesaria para terminar a tiempo
    # ══════════════════════════════════════════════
    st.markdown("### Velocidad Necesaria")

    pendientes = total - terminadas
    if days_to_competition > 0 and pendientes > 0:
        tasks_per_week = round(pendientes / max(days_to_competition / 7, 1), 1)
        tasks_per_day = round(pendientes / max(days_to_competition, 1), 1)

        v1, v2, v3 = st.columns(3)
        v1.metric("Tareas Pendientes", pendientes)
        v2.metric("Tareas / Semana necesarias", tasks_per_week)
        v3.metric("Tareas / Dia necesarias", tasks_per_day)

        st.caption(
            f"Para terminar las {pendientes} tareas restantes antes del "
            f"{competition_date.strftime('%d/%m/%Y')}, el equipo necesita completar "
            f"**{tasks_per_week} tareas por semana** ({tasks_per_day} por dia)."
        )
    elif pendientes == 0:
        st.success("Todas las tareas estan terminadas.")
    else:
        st.error(
            f"La competencia ya paso y quedan **{pendientes} tareas sin terminar**."
        )
