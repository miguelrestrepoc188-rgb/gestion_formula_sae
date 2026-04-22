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

    # Duración real del proyecto: filtrar al año predominante para excluir outliers
    all_dates = pd.concat([df["fecha_inicio"].dropna(), df["fecha_fin"].dropna()])
    if not all_dates.empty:
        mode_year = all_dates.dt.year.mode().iloc[0]
        valid_starts = df["fecha_inicio"].dropna()
        valid_ends = df["fecha_fin"].dropna()
        valid_starts = valid_starts[valid_starts.dt.year == mode_year]
        valid_ends = valid_ends[valid_ends.dt.year == mode_year]
        fecha_min = valid_starts.min() if not valid_starts.empty else pd.NaT
        fecha_max = valid_ends.max() if not valid_ends.empty else pd.NaT
    else:
        fecha_min, fecha_max = pd.NaT, pd.NaT

    if pd.notna(fecha_min) and pd.notna(fecha_max):
        dur_days = (fecha_max - fecha_min).days
        dur_weeks = max(1, round(dur_days / 7))
    else:
        dur_days = 0
        dur_weeks = 0

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Actividades Totales", total)
    c2.metric("Avance Global", f"{avance_global}%")
    c3.metric("Terminadas", terminadas, delta=f"{round(terminadas/total*100,1)}%")
    c4.metric("En Progreso", en_progreso)
    c5.metric("Duración", f"{dur_days}D", delta=f"{dur_weeks} semanas", delta_color="off")

    st.markdown("---")

    # ── Actividades Vencidas ──
    today = pd.Timestamp.now().normalize()
    df_vencidas = df[
        (df["fecha_fin"].notna()) &
        (df["fecha_fin"] < today) &
        (df["estado"] != "terminado")
    ].copy()

    n_vencidas = len(df_vencidas)
    venc_color = COLOR_DANGER if n_vencidas > 0 else COLOR_OK

    st.markdown(f"### Actividades Vencidas ({n_vencidas})")

    if not df_vencidas.empty:
        df_vencidas["dias_atraso"] = (today - df_vencidas["fecha_fin"]).dt.days
        df_vencidas = df_vencidas.sort_values("dias_atraso", ascending=False)

        # Resumen por subsistema arriba de la tabla
        venc_by_sub = df_vencidas.groupby("subsistema").size()
        resumen = " · ".join(f"**{sub}:** {count}" for sub, count in venc_by_sub.items())
        st.markdown(f"Vencidas por subsistema: {resumen}")

        display_cols = ["actividad", "microsubsistema", "responsable", "fecha_fin", "dias_atraso", "estado"]
        available = [c for c in display_cols if c in df_vencidas.columns]
        df_show = df_vencidas[available].copy()
        df_show.columns = [c.replace("_", " ").title() for c in available]
        st.dataframe(df_show.reset_index(drop=True), use_container_width=True, height=400)
    else:
        st.success("No hay actividades vencidas. El proyecto va al día.")

    st.markdown("---")

    # ── Avance por Subsistema ──
    st.markdown("### Avance por Subsistema")
    sub_progress = (
        df.groupby("subsistema")
        .agg(
            total=("id", "count"),
            terminadas=("estado", lambda x: (x == "terminado").sum()),
        )
        .reset_index()
    )
    sub_progress["avance"] = (sub_progress["terminadas"] / sub_progress["total"] * 100).round(1)
    sub_progress = sub_progress.sort_values("avance", ascending=True)

    fig_sub = go.Figure()
    fig_sub.add_trace(go.Bar(
        y=sub_progress["subsistema"],
        x=sub_progress["avance"],
        orientation="h",
        marker=dict(
            color=sub_progress["avance"],
            colorscale=[[0, MORADO_OSCURO], [0.5, LILA], [1, AMARILLO_NEON]],
            line=dict(width=0),
        ),
        text=sub_progress.apply(
            lambda r: f"{r['avance']:.0f}% ({int(r['terminadas'])}/{int(r['total'])})", axis=1
        ),
        textposition="outside",
        textfont=dict(color=BLANCO, size=11),
    ))
    fig_sub = plotly_dark_layout(fig_sub, height=max(250, len(sub_progress) * 45))
    fig_sub.update_xaxes(range=[0, 115], title="Avance (%)")
    fig_sub.update_yaxes(title="")
    st.plotly_chart(fig_sub, use_container_width=True)

    st.markdown("---")

    # ── Dos columnas: avance por microsubsistema + estados ──
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

    # ── Avance CAD / FEM por Microsubsistema ──
    CAD_KEYWORDS = r"(?i)\b(cad|fem|fea|simulaci[oó]n|modelo\s*3d|renderiz|dise[ñn]o\s*3d|sketch|solidworks)\b"
    # Paquetes que son íntegramente CAD/FEM aunque sus actividades no tengan esa keyword
    CAD_PAQUETES = r"(?i)(porta.?diferencial|porta diferencial)"
    df_cad = df[
        df["actividad"].str.contains(CAD_KEYWORDS, na=False) |
        df.get("entregable", pd.Series(dtype=str)).str.contains(CAD_KEYWORDS, na=False) |
        df.get("paquete", pd.Series(dtype=str)).str.contains(CAD_PAQUETES, na=False)
    ]

    if not df_cad.empty:
        st.markdown("### Avance CAD / FEM por Microsubsistema")

        cad_progress = (
            df_cad.groupby("microsubsistema")
            .agg(
                total=("id", "count"),
                terminadas=("estado", lambda x: (x == "terminado").sum()),
            )
            .reset_index()
        )
        cad_progress["avance"] = (cad_progress["terminadas"] / cad_progress["total"] * 100).round(1)
        cad_progress = cad_progress.sort_values("avance", ascending=True)

        cad_col_left, cad_col_right = st.columns([3, 2])

        with cad_col_left:
            fig_cad = go.Figure()
            fig_cad.add_trace(go.Bar(
                y=cad_progress["microsubsistema"],
                x=cad_progress["avance"],
                orientation="h",
                marker=dict(
                    color=cad_progress["avance"],
                    colorscale=[[0, MORADO_OSCURO], [0.5, LILA], [1, AMARILLO_NEON]],
                    line=dict(width=0),
                ),
                text=cad_progress.apply(
                    lambda r: f"{r['avance']:.0f}% ({int(r['terminadas'])}/{int(r['total'])})", axis=1
                ),
                textposition="outside",
                textfont=dict(color=BLANCO, size=11),
            ))
            fig_cad = plotly_dark_layout(fig_cad, height=max(300, len(cad_progress) * 35))
            fig_cad.update_xaxes(range=[0, 115], title="Avance (%)")
            fig_cad.update_yaxes(title="")
            st.plotly_chart(fig_cad, use_container_width=True)

        with cad_col_right:
            total_cad = len(df_cad)
            terminadas_cad = (df_cad["estado"] == "terminado").sum()
            pendientes_cad = total_cad - terminadas_cad
            pct_cad = round(terminadas_cad / total_cad * 100, 1)

            fig_cad_pie = go.Figure(data=[go.Pie(
                labels=[f"Terminadas ({terminadas_cad})", f"Pendientes ({pendientes_cad})"],
                values=[terminadas_cad, pendientes_cad],
                hole=0.6,
                marker=dict(
                    colors=[LILA, BORDER_SUBTLE],
                    line=dict(color=BG_PRIMARY, width=2),
                ),
                textfont=dict(color=BLANCO, size=12),
                textinfo="label",
            )])
            pct_terminadas = round(terminadas_cad / total_cad * 100, 1)
            pct_pendientes = round(pendientes_cad / total_cad * 100, 1)
            fig_cad_pie.update_layout(
                annotations=[
                    dict(
                        text=f"{pct_terminadas:.0f}%",
                        x=0.5, y=0.55, font=dict(size=24, color=LILA, family="Poppins"),
                        showarrow=False,
                    ),
                    dict(
                        text=f"{total_cad} tareas",
                        x=0.5, y=0.42, font=dict(size=12, color=TEXT_MUTED, family="Poppins"),
                        showarrow=False,
                    ),
                ],
            )
            fig_cad_pie = plotly_dark_layout(fig_cad_pie, height=350)
            st.plotly_chart(fig_cad_pie, use_container_width=True)

        # ── Última tarea CAD/FEM por microsubsistema ──
        st.markdown("#### Última tarea CAD/FEM por microsubsistema")

        df_cad_dated = df_cad[df_cad["fecha_fin"].notna()].copy()

        def _last_cad_tasks(df_sub):
            """Devuelve la tarea con fecha_fin más tardía por microsubsistema.
            Si hay empate de fecha, toma la última en la secuencia del cronograma."""
            return (
                df_sub.reset_index()
                .sort_values(["fecha_fin", "index"], ascending=[False, False])
                .groupby("microsubsistema", as_index=False)
                .first()[["microsubsistema", "actividad", "fecha_fin", "estado"]]
                .sort_values("microsubsistema")
            )

        df_dym_cad = df_cad_dated[df_cad_dated["subsistema"] == "DYM"]
        df_elec_cad = df_cad_dated[df_cad_dated["subsistema"] == "Electrónica"]

        last_dym = _last_cad_tasks(df_dym_cad) if not df_dym_cad.empty else pd.DataFrame()
        last_elec = _last_cad_tasks(df_elec_cad) if not df_elec_cad.empty else pd.DataFrame()

        st.markdown("**DYM**")
        if not last_dym.empty:
            last_dym = last_dym.copy()
            last_dym["fecha_fin"] = last_dym["fecha_fin"].dt.strftime("%d/%m/%Y")
            last_dym.columns = ["Microsubsistema", "Última tarea CAD/FEM", "Fecha fin", "Estado"]
            st.dataframe(last_dym.reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.info("No hay tareas CAD/FEM con fechas en DYM.")

        st.markdown("**Electrónica**")
        if not last_elec.empty:
            last_elec = last_elec.copy()
            last_elec["fecha_fin"] = last_elec["fecha_fin"].dt.strftime("%d/%m/%Y")
            last_elec.columns = ["Microsubsistema", "Última tarea CAD/FEM", "Fecha fin", "Estado"]
            st.dataframe(last_elec.reset_index(drop=True), use_container_width=True, hide_index=True)
        else:
            st.info("No hay tareas CAD/FEM con fechas en Electrónica.")

    else:
        st.markdown("### Avance CAD / FEM por Microsubsistema")
        st.info("No se encontraron actividades CAD/FEM en los datos.")

    st.markdown("---")

    # ── Avance Planos por Microsubsistema ──
    # Solo planos de manufactura (DYM): excluye "planos eléctricos" de Electrónica
    PLANOS_KEYWORDS = r"(?i)\b(plano|planos|drawing|dibujo técnico|dibujo)\b"
    PLANOS_EXCLUIR = r"(?i)(el[eé]ctric|electr[oó]nic|pcb|esquem)"
    df_planos_raw = df[df["actividad"].str.contains(PLANOS_KEYWORDS, na=False) |
                       df.get("entregable", pd.Series(dtype=str)).str.contains(PLANOS_KEYWORDS, na=False)]
    df_planos = df_planos_raw[
        ~df_planos_raw["actividad"].str.contains(PLANOS_EXCLUIR, na=False) &
        ~df_planos_raw.get("entregable", pd.Series(dtype=str)).str.contains(PLANOS_EXCLUIR, na=False)
    ]

    if not df_planos.empty:
        st.markdown("### Avance Planos por Microsubsistema")

        planos_progress = (
            df_planos.groupby("microsubsistema")
            .agg(
                total=("id", "count"),
                terminadas=("estado", lambda x: (x == "terminado").sum()),
            )
            .reset_index()
        )
        planos_progress["avance"] = (planos_progress["terminadas"] / planos_progress["total"] * 100).round(1)
        planos_progress = planos_progress.sort_values("avance", ascending=True)

        planos_col_left, planos_col_right = st.columns([3, 2])

        with planos_col_left:
            fig_planos = go.Figure()
            fig_planos.add_trace(go.Bar(
                y=planos_progress["microsubsistema"],
                x=planos_progress["avance"],
                orientation="h",
                marker=dict(
                    color=planos_progress["avance"],
                    colorscale=[[0, MORADO_OSCURO], [0.5, LILA], [1, AMARILLO_NEON]],
                    line=dict(width=0),
                ),
                text=planos_progress.apply(
                    lambda r: f"{r['avance']:.0f}% ({int(r['terminadas'])}/{int(r['total'])})", axis=1
                ),
                textposition="outside",
                textfont=dict(color=BLANCO, size=11),
            ))
            fig_planos = plotly_dark_layout(fig_planos, height=max(300, len(planos_progress) * 35))
            fig_planos.update_xaxes(range=[0, 115], title="Avance (%)")
            fig_planos.update_yaxes(title="")
            st.plotly_chart(fig_planos, use_container_width=True)

        with planos_col_right:
            total_planos = len(df_planos)
            terminadas_planos = (df_planos["estado"] == "terminado").sum()
            pendientes_planos = total_planos - terminadas_planos
            pct_terminadas_planos = round(terminadas_planos / total_planos * 100, 1)

            fig_planos_pie = go.Figure(data=[go.Pie(
                labels=[f"Terminadas ({terminadas_planos})", f"Pendientes ({pendientes_planos})"],
                values=[terminadas_planos, pendientes_planos],
                hole=0.6,
                marker=dict(
                    colors=[LILA, BORDER_SUBTLE],
                    line=dict(color=BG_PRIMARY, width=2),
                ),
                textfont=dict(color=BLANCO, size=12),
                textinfo="label",
            )])
            fig_planos_pie.update_layout(
                annotations=[
                    dict(
                        text=f"{pct_terminadas_planos:.0f}%",
                        x=0.5, y=0.55, font=dict(size=24, color=LILA, family="Poppins"),
                        showarrow=False,
                    ),
                    dict(
                        text=f"{total_planos} tareas",
                        x=0.5, y=0.42, font=dict(size=12, color=TEXT_MUTED, family="Poppins"),
                        showarrow=False,
                    ),
                ],
            )
            fig_planos_pie = plotly_dark_layout(fig_planos_pie, height=350)
            st.plotly_chart(fig_planos_pie, use_container_width=True)
    else:
        st.markdown("### Avance Planos por Microsubsistema")
        st.info("No se encontraron actividades de Planos en los datos.")

    st.markdown("---")

    # ── Carga por Responsable ──
    st.markdown("### Carga por Responsable")
    df_activas = df[df["estado"].isin(["en_progreso", "no_iniciado", "bloqueado"])].copy()

    if not df_activas.empty and "responsable" in df_activas.columns:
        import re

        # Nombres genéricos que NO son personas reales
        GENERIC_NAMES = {"todos", "sin asignar", "no definido", "nan", "",
                         "microsubsistema", "subsistema", "equipo", "team"}
        # Nombres de subsistemas/microsubsistemas del proyecto
        team_names_lower = set()
        for col in ["subsistema", "microsubsistema"]:
            if col in df.columns:
                for val in df[col].dropna().unique():
                    team_names_lower.add(str(val).strip().lower())

        def is_generic(name):
            low = name.strip().lower()
            if low in GENERIC_NAMES:
                return True
            if low in team_names_lower:
                return True
            # Prefijos de grupo: "Lideres X", "Equipo X"
            if re.match(r"^(l[ií]deres?|equipo|team)\b", low):
                return True
            return False

        rows_resp = []
        for _, row in df_activas.iterrows():
            raw = str(row["responsable"]).strip()
            micro = str(row.get("microsubsistema", "")).strip()

            if pd.isna(row["responsable"]) or raw.lower() in ("", "nan"):
                continue

            parts = re.split(r'\s*[,/]\s*|\s+[eEyY]\s+', raw)
            parts = [p.strip() for p in parts if p.strip()]

            for p in parts:
                if is_generic(p):
                    continue
                label = f"{p} — {micro}" if micro and micro.lower() not in ("", "nan") else p
                rows_resp.append({"responsable_ind": label, "estado": row["estado"]})

        if not rows_resp:
            st.info("No hay responsables individuales asignados a tareas activas.")
        else:
            df_resp = pd.DataFrame(rows_resp)
            resp_counts = df_resp.groupby("responsable_ind").agg(
                total=("estado", "count"),
                en_progreso=("estado", lambda x: (x == "en_progreso").sum()),
                no_iniciado=("estado", lambda x: (x == "no_iniciado").sum()),
                bloqueado=("estado", lambda x: (x == "bloqueado").sum()),
            ).reset_index().sort_values("total", ascending=True)

            # Top 20 con más carga
            resp_counts = resp_counts.tail(20)

            fig_resp = go.Figure()
            fig_resp.add_trace(go.Bar(
                y=resp_counts["responsable_ind"],
                x=resp_counts["en_progreso"],
                name="En progreso",
                orientation="h",
                marker=dict(color=LILA),
            ))
            fig_resp.add_trace(go.Bar(
                y=resp_counts["responsable_ind"],
                x=resp_counts["no_iniciado"],
                name="No iniciado",
                orientation="h",
                marker=dict(color=AZUL_ELECTRICO),
            ))
            fig_resp.add_trace(go.Bar(
                y=resp_counts["responsable_ind"],
                x=resp_counts["bloqueado"],
                name="Bloqueado",
                orientation="h",
                marker=dict(color=COLOR_DANGER),
            ))

            fig_resp = plotly_dark_layout(fig_resp, height=max(350, len(resp_counts) * 30))
            fig_resp.update_layout(barmode="stack")
            fig_resp.update_xaxes(title="Tareas pendientes")
            fig_resp.update_yaxes(title="")
            st.plotly_chart(fig_resp, use_container_width=True)
    else:
        st.info("No hay tareas activas para mostrar carga.")

    st.markdown("---")

    # ── Data Quality ──
    st.markdown("### Calidad de Datos")
    if "quality_score" in df.columns:
        avg_quality = df["quality_score"].mean()
        quality_color = COLOR_OK if avg_quality > 70 else COLOR_WARNING if avg_quality > 40 else COLOR_DANGER

        qc1, qc2, qc3, qc4 = st.columns(4)
        df_no_term = df[df["estado"] != "terminado"]
        sin_dur = len(df_no_term[df_no_term["duracion_dias"].isna()])
        sin_resp = len(df_no_term[df_no_term["responsable"].apply(
            lambda x: pd.isna(x) or str(x).strip().lower() in ["", "nan", "no definido"]
        )])
        sin_pred = len(df_no_term[df_no_term["predecesores"].apply(
            lambda x: not isinstance(x, list) or len(x) == 0
        )])
        sin_fecha = len(df_no_term[df_no_term["fecha_inicio"].isna()])

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
