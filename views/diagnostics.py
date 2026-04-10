"""
Vista de diagnóstico: calidad de datos y checklist de compliance FSAE.
"""
import streamlit as st
import pandas as pd
from config import (
    COLOR_OK, COLOR_WARNING, COLOR_DANGER, TEXT_MUTED, BLANCO,
    LILA, AMARILLO_NEON,
)


def render_diagnostics(df: pd.DataFrame, report: dict):
    """Renderiza el reporte de diagnóstico."""

    st.markdown("### Diagnóstico de Datos")

    # ── Resumen de limpieza ──
    st.markdown("#### Pipeline de Limpieza")
    c1, c2, c3 = st.columns(3)
    c1.metric("Actividades originales", report.get("total_raw", 0))
    c2.metric("Total final", report.get("total_final", 0))
    c3.metric("Fechas corregidas", report.get("fechas_corregidas", 0))

    st.markdown("---")

    # ── Detalle de correcciones de fecha ──
    date_fixes = report.get("date_fixes_detail", [])
    if date_fixes:
        st.markdown("#### Correcciones de Fecha Aplicadas")
        fixes_df = pd.DataFrame(date_fixes)
        st.dataframe(fixes_df, use_container_width=True)

    # ── Quality Issues breakdown ──
    st.markdown("#### Problemas de Calidad por Actividad")
    quality_summary = report.get("quality_summary", {})

    for issue, count in quality_summary.items():
        color = COLOR_DANGER if count > 30 else COLOR_WARNING if count > 10 else COLOR_OK
        label = {
            "sin_duracion": "Sin Duración",
            "sin_fecha_inicio": "Sin Fecha de Inicio",
            "sin_responsable": "Sin Responsable Definido",
            "sin_predecesores": "Sin Predecesores",
        }.get(issue, issue)

        st.markdown(
            f"<span style='color:{color}; font-weight:600'>{label}: {count} actividades</span>",
            unsafe_allow_html=True,
        )

    # ── Actividades con peor quality score ──
    if "quality_score" in df.columns:
        st.markdown("---")
        st.markdown("#### Actividades con Peor Calidad de Datos")
        worst = df.nsmallest(20, "quality_score")[
            ["id", "actividad", "subsistema", "microsubsistema",
             "quality_score", "quality_issues"]
        ].copy()
        worst["quality_issues"] = worst["quality_issues"].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else str(x)
        )
        st.dataframe(worst.reset_index(drop=True), use_container_width=True)


    st.markdown("---")

    # ── FSAE Compliance Checklist ──
    st.markdown("### Checklist de Compliance FSAE 2026")

    checks = [
        {
            "item": "Electrical System Form (ESF)",
            "rule": "EV.2.1 / PS Table PS-1",
            "status": _check_activity_exists(df, "ESF"),
            "severity": "Grounds for Removal (-20pts/día)",
        },
        {
            "item": "Structural Equivalency Spreadsheet (SES)",
            "rule": "F.2.1 / PS Table PS-1",
            "status": _check_activity_exists(df, "SES"),
            "severity": "Grounds for Removal (-20pts/día)",
        },
        {
            "item": "Design Briefing",
            "rule": "S.4.3",
            "status": _check_activity_exists(df, "Design Briefing"),
            "severity": "Removed from Design Event (0 pts)",
        },
        {
            "item": "Vehicle Drawings (3 vistas)",
            "rule": "S.4.4",
            "status": _check_activity_exists(df, "Vehicle Drawings"),
            "severity": "Removed from Design Event",
        },
        {
            "item": "Cost Report",
            "rule": "S.3.4",
            "status": _check_activity_exists(df, "Cost Report"),
            "severity": "Removed from Cost Event (0 pts)",
        },
        {
            "item": "Shutdown Circuit (BSPD, IMD, AMS, BOTS, HVD)",
            "rule": "EV.7",
            "status": _check_activity_exists(df, "shutdown"),
            "severity": "Falla en Technical Inspection",
        },
        {
            "item": "TSAL (Tractive System Active Light)",
            "rule": "EV.6",
            "status": _check_activity_exists(df, "TSAL"),
            "severity": "Falla en Technical Inspection",
        },
        {
            "item": "Rain Test Preparation",
            "rule": "IN.13",
            "status": _check_activity_exists(df, "Rain Test"),
            "severity": "No aprueba inspección",
        },
        {
            "item": "Brake Test Preparation",
            "rule": "IN.14",
            "status": _check_activity_exists(df, "Brake Test"),
            "severity": "No puede correr eventos dinámicos",
        },
        {
            "item": "Tilt Test Preparation",
            "rule": "IN.11",
            "status": _check_activity_exists(df, "Tilt Test"),
            "severity": "No aprueba inspección",
        },
        {
            "item": "Battery Isolation Test",
            "rule": "IN.5 / EV.5",
            "status": _check_activity_exists(df, "aislamiento"),
            "severity": "No aprueba battery inspection",
        },
        {
            "item": "BMS Validación",
            "rule": "EV.5",
            "status": _check_activity_exists(df, "BMS"),
            "severity": "Falla en Technical Inspection",
        },
    ]

    for check in checks:
        icon = "✅" if check["status"] else "❌"
        color = COLOR_OK if check["status"] else COLOR_DANGER
        st.markdown(
            f"<div style='padding:8px 12px; border-left:3px solid {color}; "
            f"margin-bottom:6px; background:rgba(0,0,0,0.2); border-radius:4px'>"
            f"<b>{icon} {check['item']}</b> "
            f"<span style='color:{TEXT_MUTED}; font-size:0.8em'>({check['rule']})</span><br>"
            f"<small style='color:{color}'>{check['severity']}</small>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _check_activity_exists(df: pd.DataFrame, keyword: str) -> bool:
    """Verifica si existe al menos una actividad que contenga el keyword."""
    keyword_lower = keyword.lower()
    for col in ["actividad", "entregable", "paquete"]:
        if col in df.columns:
            matches = df[col].str.lower().str.contains(keyword_lower, na=False)
            if matches.any():
                return True
    return False
