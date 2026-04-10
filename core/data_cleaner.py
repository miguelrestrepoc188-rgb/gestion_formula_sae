"""
Pipeline de limpieza y migración de datos del Excel de cronograma.
Convierte el Excel crudo de Kratos en un DataFrame normalizado y validado.
"""
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from config import ESTADO_NORMALIZATION, ESTADOS_VALIDOS


def load_excel(filepath: str) -> pd.DataFrame:
    """Lee el Excel crudo y extrae la hoja 'Diseño a Detalle' con headers correctos."""
    df_raw = pd.read_excel(filepath, sheet_name="Diseño a Detalle", header=None)

    # Palabras clave para detectar cada columna → nombre interno
    header_keywords = [
        (["id"], "id"),
        (["subsistema"], "subsistema"),
        (["microsubsistema", "micro"], "microsubsistema"),
        (["paquete"], "paquete"),
        (["actividad predecesora", "predecesora", "predecesor"], "predecesores_raw"),
        (["actividad"], "actividad"),
        (["entregable"], "entregable"),
        (["responsable"], "responsable"),
        (["fecha inicial", "fecha inicio", "inicio"], "fecha_inicio"),
        (["fecha final", "fecha fin", "fin"], "fecha_fin"),
        (["estado"], "estado_raw"),
    ]

    # Buscar la fila que contiene los headers
    header_row = None
    for i in range(min(10, len(df_raw))):
        row_vals = [str(v).strip().lower() for v in df_raw.iloc[i] if pd.notna(v)]
        if any(h in row_vals for h in ["id tarea", "actividad", "subsistema"]):
            header_row = i
            break

    if header_row is None:
        header_row = 1  # fallback

    # Leer headers reales del Excel
    raw_headers = df_raw.iloc[header_row].tolist()

    # Encontrar columnas que coinciden (matching por keywords)
    col_indices = []
    col_names = []
    used_internals = set()

    for idx, h in enumerate(raw_headers):
        if pd.isna(h):
            continue
        h_clean = str(h).strip().lower()
        for keywords, internal in header_keywords:
            if internal in used_internals:
                continue
            if any(kw in h_clean for kw in keywords):
                col_indices.append(idx)
                col_names.append(internal)
                used_internals.add(internal)
                break

    # Extraer datos desde la fila siguiente a los headers
    df = df_raw.iloc[header_row + 1:, col_indices].copy()
    df.columns = col_names

    # Asegurar que existan las columnas mínimas requeridas
    for required in ["id", "actividad"]:
        if required not in df.columns:
            raise ValueError(
                f"No se encontró la columna '{required}' en el Excel. "
                f"Headers detectados: {[str(h).strip() for h in raw_headers if pd.notna(h)]}"
            )

    df = df.dropna(subset=["id"]).reset_index(drop=True)

    return df


def normalize_estados(df: pd.DataFrame) -> pd.DataFrame:
    """Normaliza los 9+ estados inconsistentes a 4 estados canónicos."""
    df["estado"] = (
        df["estado_raw"]
        .str.strip()
        .str.lower()
        .map(ESTADO_NORMALIZATION)
        .fillna("no_iniciado")
    )
    return df


def fix_dates(df: pd.DataFrame) -> tuple[pd.DataFrame, list[dict]]:
    """
    Corrige fechas invertidas y convierte a datetime.
    Retorna el DataFrame corregido y un log de correcciones.
    """
    fixes = []

    df["fecha_inicio"] = pd.to_datetime(df["fecha_inicio"], errors="coerce")
    df["fecha_fin"] = pd.to_datetime(df["fecha_fin"], errors="coerce")

    for idx, row in df.iterrows():
        fi, ff = row["fecha_inicio"], row["fecha_fin"]

        # Corregir fechas invertidas
        if pd.notna(fi) and pd.notna(ff) and fi > ff:
            df.at[idx, "fecha_inicio"] = ff
            df.at[idx, "fecha_fin"] = fi
            fixes.append({
                "id": row["id"],
                "tipo": "fechas_invertidas",
                "original": f"{fi.date()} → {ff.date()}",
                "corregido": f"{ff.date()} → {fi.date()}",
            })

    # Calcular duración siempre desde las fechas
    df["duracion_dias"] = df.apply(
        lambda row: max((row["fecha_fin"] - row["fecha_inicio"]).days, 0)
        if pd.notna(row["fecha_inicio"]) and pd.notna(row["fecha_fin"]) else None,
        axis=1,
    )
    df["duracion_semanas"] = df["duracion_dias"].apply(
        lambda d: max(1, round(d / 7)) if pd.notna(d) and d > 0 else d
    )

    return df, fixes


def parse_predecessors(df: pd.DataFrame) -> pd.DataFrame:
    """
    Intenta mapear predecesores en texto libre a IDs de actividad.
    Los que no se puedan mapear quedan como texto para revisión manual.
    """
    # Construir índice inverso: nombre de actividad/paquete → ID
    name_to_ids = {}
    for _, row in df.iterrows():
        rid = row["id"]
        for field in ["actividad", "paquete", "entregable"]:
            val = str(row[field]).strip().lower()
            if val and val != "nan":
                if val not in name_to_ids:
                    name_to_ids[val] = []
                name_to_ids[val].append(rid)

    def resolve_predecessor(raw_text, current_id):
        if pd.isna(raw_text) or str(raw_text).strip() == "":
            return []
        text = str(raw_text).strip()

        # Si ya es un ID válido (ej: DYM-AE-001)
        if text in df["id"].values:
            return [text]

        # Intentar match por nombre
        key = text.lower().strip()
        matches = name_to_ids.get(key, [])
        # Excluir auto-referencia
        matches = [m for m in matches if m != current_id]

        if matches:
            return matches

        # No se pudo resolver — devolver como texto con flag
        return [f"?{text}"]

    df["predecesores"] = df.apply(
        lambda row: resolve_predecessor(row["predecesores_raw"], row["id"]),
        axis=1
    )

    return df


def flag_quality_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Genera flags de calidad de datos para cada actividad."""
    issues = []

    for _, row in df.iterrows():
        row_issues = []
        terminada = row.get("estado", "") in ["terminado"]

        if not terminada and (pd.isna(row["duracion_dias"]) or row["duracion_dias"] <= 0):
            row_issues.append("sin_duracion")

        if not terminada and pd.isna(row["fecha_inicio"]):
            row_issues.append("sin_fecha_inicio")

        if not terminada and pd.isna(row["fecha_fin"]):
            row_issues.append("sin_fecha_fin")

        if not terminada:
            resp = str(row["responsable"]).strip().lower()
            if resp in ["no definido", "nan", ""]:
                row_issues.append("sin_responsable")

            # Predecesores no resueltos
            preds = row.get("predecesores", [])
            if any(str(p).startswith("?") for p in preds):
                row_issues.append("predecesor_no_resuelto")

            if not preds or len(preds) == 0:
                row_issues.append("sin_predecesores")

        issues.append(row_issues)

    df["quality_issues"] = issues
    df["quality_score"] = df["quality_issues"].apply(
        lambda x: max(0, 100 - len(x) * 20)
    )

    return df


def normalize_responsables(df: pd.DataFrame) -> pd.DataFrame:
    """
    Divide entradas con múltiples responsables en una lista.
    Ej: 'Valerin e Isabel' → ['Valerin', 'Isabel']
    Separa por: ' e ', ' y ', ',', '/'
    """
    import re

    # Nombres exactos que indican grupo/equipo (se resuelven al micro de la fila)
    generic_keywords = {"todos", "microsubsistema", "subsistema", "no definido"}
    # Nombres de subsistemas y microsubsistemas reales del Excel
    team_names = set()
    for col in ["subsistema", "microsubsistema"]:
        if col in df.columns:
            for val in df[col].dropna().unique():
                team_names.add(str(val).strip().lower())
    # Prefijos que combinados con equipo son grupo (ej: "Lideres Electrónica")
    group_prefixes = {"lideres", "líderes", "lider", "líder", "equipo", "team"}

    def classify_name(name):
        """Retorna ('person', name) o ('group', name)."""
        low = name.strip().lower()
        # Keyword genérico → grupo
        if low in generic_keywords:
            return ("group", name)
        # Nombre exacto de subsistema/micro → grupo
        if low in team_names:
            return ("group", name)
        # Prefijo solo ("Lideres") o con equipo ("Lideres Electrónica") → grupo
        parts = low.split(None, 1)
        if parts[0] in group_prefixes:
            return ("group", name)
        # Contiene nombre de equipo ("Lideres Electrónica" no spliteado)
        for tn in team_names:
            if tn in low:
                return ("group", name)
        return ("person", name)

    def split_names(val):
        if pd.isna(val) or str(val).strip() in ["", "nan"]:
            return [], []
        text = str(val).strip()
        parts = re.split(r'\s*[,/]\s*|\s+[eEyY]\s+', text)
        parts = [p.strip() for p in parts if p.strip()]
        persons, groups = [], []
        for p in parts:
            kind, n = classify_name(p)
            if kind == "group":
                groups.append(n)
            else:
                persons.append(n)
        return persons, groups

    # Paso 1: recopilar nombres de personas y su frecuencia para fuzzy fix
    from difflib import SequenceMatcher
    from collections import Counter

    all_raw_names = []
    for val in df["responsable"].dropna():
        persons, _ = split_names(val)
        all_raw_names.extend(persons)
    freq = Counter(all_raw_names)

    # Paso 2: agrupar nombres similares → elegir el canónico
    def pick_canonical(a, b):
        """Entre dos nombres similares, elige el correcto.
        - Si uno es prefijo del otro (truncación: Gom→Goma), elige el más largo.
        - Si no, elige el más corto (el más largo probablemente tiene letras de más: Esteaban→Esteban).
        """
        la, lb = a.lower(), b.lower()
        if la.startswith(lb) or lb.startswith(la):
            return a if len(a) >= len(b) else b
        return a if len(a) <= len(b) else b

    canonical = list(freq.keys())
    name_map = {}

    used = set()
    for name in sorted(canonical, key=lambda n: -freq[n]):
        if name in used:
            continue
        for other in canonical:
            if other == name or other in used:
                continue
            ratio = SequenceMatcher(None, name.lower(), other.lower()).ratio()
            if ratio >= 0.75:
                winner = pick_canonical(name, other)
                loser = other if winner == name else name
                name_map[loser] = winner
                used.add(loser)
        used.add(name)

    def fix_name(n):
        return name_map.get(n, n)

    # Mapa inverso: nombre_lower → nombre_original (capitalizado) del Excel
    team_name_original = {}
    for col in ["subsistema", "microsubsistema"]:
        if col in df.columns:
            for val in df[col].dropna().unique():
                team_name_original[str(val).strip().lower()] = str(val).strip()

    def resolve_group(raw_group_name, row):
        """Resuelve un grupo genérico al microsubsistema real de la fila."""
        low = raw_group_name.strip().lower()
        micro = str(row.get("microsubsistema", "")).strip()
        sub = str(row.get("subsistema", "")).strip()
        # "Todos", "Microsubsistema", "No Definido", "Subsistema" → usar el micro de la fila
        if low in generic_keywords:
            if micro and micro.lower() not in ["", "nan"]:
                return micro
            if sub and sub.lower() not in ["", "nan"]:
                return sub
            return None
        # Buscar qué nombre de equipo real está contenido en el texto
        # Ej: "Subsistema de chasis" → contiene "chasis" → "Chasis"
        # Ej: "Lideres Electrónica" → contiene "electrónica" → "Electrónica"
        for tn_low, tn_orig in team_name_original.items():
            if tn_low in low and tn_low not in generic_keywords:
                return tn_orig
        # Fallback: usar micro de la fila
        if micro and micro.lower() not in ["", "nan"]:
            return micro
        return raw_group_name

    def build_lists(row):
        persons, groups = split_names(row["responsable"])
        persons = [fix_name(n) for n in persons]
        micro = str(row.get("microsubsistema", "")).strip()
        if micro and micro.lower() not in ["", "nan", "microsubsistema", "no definido"]:
            persons = [f"{n} {micro}" for n in persons]
        resolved_groups = []
        for g in groups:
            resolved = resolve_group(g, row)
            if resolved:
                resolved_groups.append(resolved)
        return persons, resolved_groups

    results = df.apply(build_lists, axis=1)
    df["responsables_list"] = results.apply(lambda x: x[0])
    df["responsables_grupos"] = results.apply(lambda x: x[1])
    return df


def compute_progress(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula avance basado en estado (si no hay % explícito)."""
    avance_map = {
        "no_iniciado": 0,
        "en_progreso": 50,
        "terminado": 100,
        "bloqueado": 0,
    }
    df["avance_pct"] = df["estado"].map(avance_map).fillna(0)
    return df



def run_pipeline(filepath: str) -> tuple[pd.DataFrame, dict]:
    """
    Ejecuta el pipeline completo de limpieza.
    Retorna: (DataFrame limpio, reporte de diagnóstico)
    """
    report = {"timestamp": datetime.now().isoformat()}

    # 1. Cargar
    df = load_excel(filepath)
    report["total_raw"] = len(df)

    # 2. Normalizar estados
    df = normalize_estados(df)
    estados_originales = df["estado_raw"].str.strip().str.lower().nunique()
    report["estados_originales"] = estados_originales
    report["estados_normalizados"] = len(ESTADOS_VALIDOS)

    # 3. Corregir fechas
    df, date_fixes = fix_dates(df)
    report["fechas_corregidas"] = len(date_fixes)
    report["date_fixes_detail"] = date_fixes

    # 4. Parsear predecesores
    df = parse_predecessors(df)
    unresolved = df["predecesores"].apply(
        lambda x: sum(1 for p in x if str(p).startswith("?"))
    ).sum()
    report["predecesores_no_resueltos"] = int(unresolved)

    # 5. Quality flags
    df = flag_quality_issues(df)
    report["quality_summary"] = {
        "sin_duracion": int((df["quality_issues"].apply(lambda x: "sin_duracion" in x)).sum()),
        "sin_fecha_inicio": int((df["quality_issues"].apply(lambda x: "sin_fecha_inicio" in x)).sum()),
        "sin_responsable": int((df["quality_issues"].apply(lambda x: "sin_responsable" in x)).sum()),
        "sin_predecesores": int((df["quality_issues"].apply(lambda x: "sin_predecesores" in x)).sum()),
    }

    # 6. Normalizar responsables (split múltiples)
    df = normalize_responsables(df)

    # 7. Calcular avance
    df = compute_progress(df)
    report["avance_global"] = round(df["avance_pct"].mean(), 1)

    report["total_final"] = len(df)

    return df, report


def export_to_json(df: pd.DataFrame, filepath: str):
    """Exporta el DataFrame limpio a JSON estructurado para backup/intercambio."""
    records = []
    for _, row in df.iterrows():
        record = {
            "id": row["id"],
            "subsistema": row.get("subsistema", ""),
            "microsubsistema": row.get("microsubsistema", ""),
            "paquete": row.get("paquete", ""),
            "actividad": row.get("actividad", ""),
            "entregable": row.get("entregable", ""),
            "responsable": row.get("responsable", ""),
            "duracion_dias": None if pd.isna(row.get("duracion_dias")) else int(row["duracion_dias"]),
            "fecha_inicio": str(row["fecha_inicio"].date()) if pd.notna(row.get("fecha_inicio")) else None,
            "fecha_fin": str(row["fecha_fin"].date()) if pd.notna(row.get("fecha_fin")) else None,
            "estado": row.get("estado", "no_iniciado"),
            "avance_pct": row.get("avance_pct", 0),
            "predecesores": row.get("predecesores", []),
            "fase": row.get("fase", "diseño"),
            "quality_issues": row.get("quality_issues", []),
            "quality_score": row.get("quality_score", 0),
        }
        records.append(record)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump({"version": "1.0", "generated": datetime.now().isoformat(),
                    "activities": records}, f, ensure_ascii=False, indent=2)
