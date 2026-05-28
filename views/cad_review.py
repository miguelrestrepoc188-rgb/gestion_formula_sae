"""
Vista: Revisión CAD
Lista de piezas por microsubsistema con criterios de revisión DFM/DFA.
"""
import json
import streamlit as st
from pathlib import Path

from config import (
    LILA, AMARILLO_NEON, TEXT_MUTED, BG_CARD, BLANCO,
    BORDER_SUBTLE, COLOR_OK, COLOR_DANGER, MORADO_OSCURO, SUBSISTEMAS
)

# ── Persistencia ──────────────────────────────────────────────────────────────
CAD_FILE = Path("data") / "cad_review.json"

# Todos los microsubsistemas disponibles (subsistema → lista)
ALL_MICROSUBSISTEMAS: dict[str, list[str]] = {
    sub_data["nombre"]: sub_data["microsubsistemas"]
    for sub_data in SUBSISTEMAS.values()
}

# Lista plana de microsubsistemas para selectbox
MICRO_LIST: list[str] = [
    micro
    for sub_data in SUBSISTEMAS.values()
    for micro in sub_data["microsubsistemas"]
]

# Color por subsistema padre (para badges)
MICRO_COLOR: dict[str, str] = {
    micro: sub_data["color"]
    for sub_data in SUBSISTEMAS.values()
    for micro in sub_data["microsubsistemas"]
}


def _load_data() -> dict:
    """Carga piezas desde JSON. Estructura: {microsubsistema: [{nombre, bd, dfm, dfa}]}"""
    if CAD_FILE.exists():
        try:
            return json.loads(CAD_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_data(data: dict) -> None:
    CAD_FILE.parent.mkdir(exist_ok=True)
    CAD_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _init_session():
    if "cad_data" not in st.session_state:
        st.session_state.cad_data = _load_data()


# ── Render principal ──────────────────────────────────────────────────────────
def render_cad_review():
    _init_session()
    data: dict = st.session_state.cad_data

    st.markdown("## Revisión CAD")
    st.markdown(
        f"<p style='color:{TEXT_MUTED}; margin-top:-12px;'>"
        "Registro y revisión de piezas por microsubsistema — "
        "Diseño, DFM y DFA."
        "</p>",
        unsafe_allow_html=True,
    )

    # ── KPIs rápidos ──────────────────────────────────────────────────────────
    total_piezas = sum(len(v) for v in data.values())
    total_bd  = sum(p["bd"]  for v in data.values() for p in v)
    total_dfm = sum(p["dfm"] for v in data.values() for p in v)
    total_dfa = sum(p["dfa"] for v in data.values() for p in v)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Piezas registradas", total_piezas)
    k2.metric("DFM aprobadas",      f"{total_dfm}/{total_piezas}")
    k3.metric("DFA aprobadas",      f"{total_dfa}/{total_piezas}")
    k4.metric("BOM",                f"{total_bd}/{total_piezas}")

    st.markdown("---")

    # ── Formulario de nueva pieza ─────────────────────────────────────────────
    with st.expander("➕ Agregar nueva pieza", expanded=False):
        col_nombre, col_micro = st.columns([2, 1])
        with col_nombre:
            nombre_pieza = st.text_input(
                "Nombre de la pieza",
                placeholder="Ej: Upright delantero izquierdo",
                key="cad_new_nombre",
            )
        with col_micro:
            micro_sel = st.selectbox(
                "Microsubsistema",
                options=MICRO_LIST,
                key="cad_new_micro",
            )

        if st.button("Agregar pieza", key="cad_add_btn"):
            nombre_pieza = nombre_pieza.strip()
            if not nombre_pieza:
                st.warning("Ingresa el nombre de la pieza.")
            else:
                bucket = data.setdefault(micro_sel, [])
                # Evitar duplicados exactos dentro del mismo microsubsistema
                if any(p["nombre"].lower() == nombre_pieza.lower() for p in bucket):
                    st.warning(f'La pieza "{nombre_pieza}" ya existe en {micro_sel}.')
                else:
                    bucket.append({"nombre": nombre_pieza, "bd": False, "dfm": False, "dfa": False})
                    _save_data(data)
                    st.success(f'Pieza "{nombre_pieza}" agregada a {micro_sel}.')
                    st.rerun()

    st.markdown("---")

    # ── Tabla de piezas por microsubsistema ───────────────────────────────────
    if not data:
        st.markdown(
            f"<div style='text-align:center; padding:60px 0; color:{TEXT_MUTED};'>"
            "Aún no hay piezas registradas. Usa el formulario de arriba para agregar."
            "</div>",
            unsafe_allow_html=True,
        )
        return

    # Recorrer microsubsistemas en el orden canónico del config
    for micro in MICRO_LIST:
        piezas = data.get(micro, [])
        if not piezas:
            continue

        color = MICRO_COLOR.get(micro, LILA)
        aprobadas = sum(1 for p in piezas if p["bd"] and p["dfm"] and p["dfa"])
        progreso = aprobadas / len(piezas) if piezas else 0

        st.markdown(
            f"<div style='display:flex; align-items:center; gap:12px; margin-bottom:4px;'>"
            f"<span style='color:{color}; font-weight:700; font-size:1.05rem;'>{micro}</span>"
            f"<span style='color:{TEXT_MUTED}; font-size:0.8rem;'>{len(piezas)} pieza(s) · "
            f"{aprobadas} completamente aprobada(s)</span>"
            f"</div>",
            unsafe_allow_html=True,
        )
        st.progress(progreso)

        # Encabezado de columnas
        h0, h1, h2, h3, h4 = st.columns([4, 1, 1, 1, 0.6])
        h1.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.75rem; "
            f"font-weight:600; text-transform:uppercase;'>DFM</div>",
            unsafe_allow_html=True,
        )
        h2.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.75rem; "
            f"font-weight:600; text-transform:uppercase;'>DFA</div>",
            unsafe_allow_html=True,
        )
        h3.markdown(
            f"<div style='text-align:center; color:{TEXT_MUTED}; font-size:0.75rem; "
            f"font-weight:600; text-transform:uppercase;'>BOM</div>",
            unsafe_allow_html=True,
        )

        changed = False
        to_delete = None

        for idx, pieza in enumerate(piezas):
            safe_key = f"{micro}_{idx}"
            c0, c1, c2, c3, c4 = st.columns([4, 1, 1, 1, 0.6])

            # Indicador visual de completitud
            all_ok = pieza["bd"] and pieza["dfm"] and pieza["dfa"]
            dot_color = COLOR_OK if all_ok else (AMARILLO_NEON if any([pieza["bd"], pieza["dfm"], pieza["dfa"]]) else COLOR_DANGER)
            c0.markdown(
                f"<div style='display:flex; align-items:center; gap:8px; height:38px;'>"
                f"<span style='color:{dot_color}; font-size:0.6rem;'>●</span>"
                f"<span style='color:{BLANCO}; font-size:0.9rem;'>{pieza['nombre']}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )

            new_dfm = c1.checkbox("", value=pieza["dfm"], key=f"dfm_{safe_key}", label_visibility="collapsed")
            new_dfa = c2.checkbox("", value=pieza["dfa"], key=f"dfa_{safe_key}", label_visibility="collapsed")
            new_bd  = c3.checkbox("", value=pieza["bd"],  key=f"bd_{safe_key}",  label_visibility="collapsed")

            if c4.button("🗑️", key=f"del_{safe_key}", help="Eliminar pieza"):
                to_delete = idx

            if new_bd != pieza["bd"] or new_dfm != pieza["dfm"] or new_dfa != pieza["dfa"]:
                pieza["bd"]  = new_bd
                pieza["dfm"] = new_dfm
                pieza["dfa"] = new_dfa
                changed = True

        if to_delete is not None:
            piezas.pop(to_delete)
            if not piezas:
                del data[micro]
            changed = True

        if changed:
            _save_data(data)
            st.rerun()

        st.markdown("<div style='margin-bottom:24px;'></div>", unsafe_allow_html=True)
