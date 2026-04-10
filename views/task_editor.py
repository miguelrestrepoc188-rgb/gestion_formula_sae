"""
Editor de tareas: los líderes pueden agregar, modificar y exportar actividades.
"""
import streamlit as st
import pandas as pd
import json
import io
from datetime import datetime, date, timedelta
from config import (
    ESTADOS_VALIDOS, ESTADO_DISPLAY, SUBSISTEMAS,
    LILA, AMARILLO_NEON, TEXT_MUTED, BG_CARD,
)


def render_task_editor(df: pd.DataFrame) -> pd.DataFrame:
    """
    Renderiza el editor de tareas. Retorna el DataFrame modificado.
    """

    st.markdown("### Editor de Actividades")

    tab_edit, tab_add, tab_export = st.tabs(["✏️ Editar Existente", "➕ Nueva Actividad", "📤 Exportar"])

    with tab_edit:
        df_modified = _render_edit_tab(df)

    with tab_add:
        df_modified = _render_add_tab(df_modified)

    with tab_export:
        _render_export_tab(df_modified)

    return df_modified


def _render_edit_tab(df: pd.DataFrame) -> pd.DataFrame:
    """Tab para editar actividades existentes."""

    # Selector de actividad
    task_options = df["id"].tolist()
    sel_task = st.selectbox(
        "Selecciona actividad a editar",
        task_options,
        format_func=lambda x: f"{x} — {df[df['id'] == x]['actividad'].values[0]}" if x in df["id"].values else x,
        key="edit_task_selector"
    )

    if not sel_task:
        return df

    row = df[df["id"] == sel_task].iloc[0]
    idx = df[df["id"] == sel_task].index[0]

    # Inicializar valores en session_state solo si no existen
    fi_val = row["fecha_inicio"].date() if pd.notna(row.get("fecha_inicio")) else date.today()
    ff_val = row["fecha_fin"].date() if pd.notna(row.get("fecha_fin")) else date.today()
    dur_val = int(row["duracion_semanas"]) if pd.notna(row.get("duracion_semanas")) else 0

    if "edit_fi" not in st.session_state:
        st.session_state.edit_fi = fi_val
    if "edit_ff" not in st.session_state:
        st.session_state.edit_ff = ff_val
    if "edit_dur" not in st.session_state:
        st.session_state.edit_dur = dur_val

    # Callbacks: sincronizar fechas ↔ duración
    def on_dates_change():
        fi = st.session_state.edit_fi
        ff = st.session_state.edit_ff
        if fi and ff and ff >= fi:
            st.session_state.edit_dur = max(1, round((ff - fi).days / 7))

    def on_dur_change():
        fi = st.session_state.edit_fi
        dur = st.session_state.edit_dur
        if fi and dur > 0:
            st.session_state.edit_ff = fi + timedelta(weeks=dur)

    col1, col2 = st.columns(2)

    with col1:
        new_estado = st.selectbox(
            "Estado",
            ESTADOS_VALIDOS,
            index=ESTADOS_VALIDOS.index(row["estado"]) if row["estado"] in ESTADOS_VALIDOS else 0,
            format_func=lambda x: ESTADO_DISPLAY.get(x, x),
            key="edit_estado"
        )

        new_resp = st.text_input(
            "Responsable",
            value=str(row["responsable"]) if pd.notna(row["responsable"]) else "",
            key="edit_resp"
        )

        new_dur = st.number_input(
            "Duración (semanas)",
            min_value=0,
            key="edit_dur",
            on_change=on_dur_change,
        )

    with col2:
        new_fi = st.date_input("Fecha Inicio", key="edit_fi", on_change=on_dates_change)
        new_ff = st.date_input("Fecha Fin", key="edit_ff", on_change=on_dates_change)

        new_avance = st.slider(
            "Avance (%)",
            0, 100,
            value=int(row.get("avance_pct", 0)),
            key="edit_avance"
        )

    # Validaciones
    if new_fi > new_ff:
        st.error("⚠️ La fecha de inicio no puede ser posterior a la fecha de fin.")

    if st.button("💾 Guardar cambios", key="edit_save", type="primary"):
        df.at[idx, "estado"] = new_estado
        df.at[idx, "responsable"] = new_resp
        df.at[idx, "duracion_semanas"] = new_dur
        df.at[idx, "duracion_dias"] = new_dur * 7
        df.at[idx, "fecha_inicio"] = pd.Timestamp(new_fi)
        df.at[idx, "fecha_fin"] = pd.Timestamp(new_ff)
        df.at[idx, "avance_pct"] = new_avance
        st.success(f"✅ Actividad {sel_task} actualizada.")
        st.rerun()

    return df


def _render_add_tab(df: pd.DataFrame) -> pd.DataFrame:
    """Tab para agregar nuevas actividades."""

    st.markdown("#### Nueva Actividad")

    col1, col2 = st.columns(2)

    with col1:
        all_subs = sorted(df["subsistema"].dropna().unique().tolist())
        new_sub = st.selectbox("Subsistema", all_subs, key="add_sub")

        all_micros = sorted(
            df[df["subsistema"] == new_sub]["microsubsistema"].dropna().unique().tolist()
        )
        new_micro = st.selectbox("Microsubsistema", all_micros + ["+ Nuevo..."], key="add_micro")
        if new_micro == "+ Nuevo...":
            new_micro = st.text_input("Nombre del nuevo microsubsistema", key="add_micro_custom")

        new_paquete = st.text_input("Paquete de Actividades", key="add_paq")
        new_actividad = st.text_input("Nombre de la Actividad", key="add_act")
        new_entregable = st.text_input("Entregable", key="add_ent")

    with col2:
        new_resp = st.text_input("Responsable", key="add_resp")
        new_dur = st.number_input("Duración (semanas)", min_value=1, value=1, key="add_dur")
        new_fi = st.date_input("Fecha Inicio", key="add_fi")
        new_ff = st.date_input("Fecha Fin", key="add_ff")
        new_estado = st.selectbox(
            "Estado",
            ESTADOS_VALIDOS,
            format_func=lambda x: ESTADO_DISPLAY.get(x, x),
            key="add_estado"
        )

    # Predecesores
    pred_options = df["id"].tolist()
    new_preds = st.multiselect("Predecesores (IDs)", pred_options, key="add_preds")

    # Generar ID automático
    prefix = f"{new_sub[:3].upper()}-{new_micro[:2].upper()}" if new_micro else "NEW"
    existing_ids = df["id"].tolist()
    counter = 1
    while f"{prefix}-{counter:03d}" in existing_ids:
        counter += 1
    suggested_id = f"{prefix}-{counter:03d}"
    new_id = st.text_input("ID de Actividad", value=suggested_id, key="add_id")

    if st.button("➕ Agregar Actividad", key="add_save", type="primary"):
        if not new_actividad.strip():
            st.error("El nombre de la actividad es obligatorio.")
        elif new_id in df["id"].values:
            st.error(f"El ID '{new_id}' ya existe.")
        elif new_fi > new_ff:
            st.error("La fecha de inicio no puede ser posterior a la fecha de fin.")
        else:
            new_row = {
                "id": new_id,
                "subsistema": new_sub,
                "microsubsistema": new_micro,
                "paquete": new_paquete,
                "actividad": new_actividad,
                "entregable": new_entregable,
                "responsable": new_resp,
                "duracion_dias": new_dur * 7,
                "duracion_semanas": new_dur,
                "fecha_inicio": pd.Timestamp(new_fi),
                "fecha_fin": pd.Timestamp(new_ff),
                "estado": new_estado,
                "avance_pct": 0,
                "predecesores": new_preds,
                "fase": "diseño",
                "quality_issues": [],
                "quality_score": 100,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            st.success(f"✅ Actividad '{new_id}' agregada exitosamente.")
            st.rerun()

    return df


def _render_export_tab(df: pd.DataFrame):
    """Tab para exportar datos."""

    st.markdown("#### Exportar datos")

    col1, col2 = st.columns(2)

    with col1:
        # JSON export
        export_data = []
        for _, row in df.iterrows():
            record = {}
            for col in df.columns:
                val = row[col]
                if isinstance(val, list):
                    record[col] = val
                elif isinstance(val, pd.Timestamp):
                    record[col] = str(val.date())
                elif pd.isna(val):
                    record[col] = None
                else:
                    record[col] = val
                    try:
                        record[col] = val.item()  # numpy types
                    except (AttributeError, ValueError):
                        pass

            export_data.append(record)

        json_str = json.dumps(
            {"version": "1.0", "exported": datetime.now().isoformat(), "activities": export_data},
            ensure_ascii=False, indent=2, default=str
        )

        st.download_button(
            "📥 Descargar JSON",
            data=json_str,
            file_name=f"kratos_schedule_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            key="export_json"
        )

    with col2:
        # Excel export — misma estructura del archivo original
        excel_cols = {
            "id": "ID tarea",
            "subsistema": "Subsistema",
            "microsubsistema": "Microsubsistema",
            "paquete": "Paquete de trabajo",
            "actividad": "Actividad",
            "entregable": "Entregable",
            "predecesores_raw": "Actividad Predecesora",
            "responsable": "Responsable",
            "fecha_inicio": "Fecha inicial",
            "fecha_fin": "Fecha Final",
            "estado": "Estado",
        }
        export_df = df[[c for c in excel_cols if c in df.columns]].copy()
        export_df.rename(columns=excel_cols, inplace=True)

        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            export_df.to_excel(writer, sheet_name="Diseño a Detalle", index=False)
            ws = writer.sheets["Diseño a Detalle"]
            from openpyxl.worksheet.table import Table, TableStyleInfo
            last_col = chr(64 + len(export_df.columns))  # A=1, B=2...
            last_row = len(export_df) + 1  # +1 por header
            table_ref = f"A1:{last_col}{last_row}"
            table = Table(displayName="Cronograma", ref=table_ref)
            table.tableStyleInfo = TableStyleInfo(
                name="TableStyleMedium9", showFirstColumn=False,
                showLastColumn=False, showRowStripes=True, showColumnStripes=False,
            )
            ws.add_table(table)
        buffer.seek(0)

        st.download_button(
            "📥 Descargar Excel",
            data=buffer,
            file_name=f"kratos_schedule_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_excel"
        )

    st.markdown("---")
    st.markdown("#### Importar JSON")
    uploaded = st.file_uploader("Cargar archivo JSON previamente exportado", type=["json"], key="import_json")
    if uploaded:
        try:
            data = json.loads(uploaded.read().decode("utf-8"))
            if "activities" in data:
                st.success(f"✅ Archivo cargado: {len(data['activities'])} actividades encontradas.")
                st.info("Recarga la aplicación para usar los datos importados.")
            else:
                st.error("El archivo no tiene el formato esperado (falta campo 'activities').")
        except Exception as e:
            st.error(f"Error leyendo archivo: {e}")
