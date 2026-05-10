"""
Módulo de historial: guarda y carga snapshots de cada carga de Excel.
Los datos se persisten en data/history.json.
"""
import json
from datetime import datetime
from pathlib import Path

import pandas as pd

HISTORY_FILE = Path("data") / "history.json"


def load_history() -> list[dict]:
    """Carga el historial desde disco. Retorna lista vacía si no existe."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return []


def save_snapshot(df: pd.DataFrame, filename: str) -> None:
    """Guarda un snapshot del estado actual del DataFrame en el historial."""
    total = len(df)
    terminadas = int((df["estado"] == "terminado").sum())
    en_progreso = int((df["estado"] == "en_progreso").sum())
    no_iniciadas = int((df["estado"] == "no_iniciado").sum())
    bloqueadas = int((df["estado"] == "bloqueado").sum())
    avance_pct = round(float(df["avance_pct"].mean()), 1) if "avance_pct" in df.columns else 0.0

    snapshot = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "filename": filename,
        "total": total,
        "terminadas": terminadas,
        "en_progreso": en_progreso,
        "no_iniciadas": no_iniciadas,
        "bloqueadas": bloqueadas,
        "avance_pct": avance_pct,
    }

    history = load_history()
    history.append(snapshot)

    HISTORY_FILE.parent.mkdir(exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def get_previous_snapshot() -> dict | None:
    """Retorna el penúltimo snapshot (la carga anterior a la actual).
    Retorna None si hay menos de 2 entradas en el historial."""
    history = load_history()
    if len(history) < 2:
        return None
    return history[-2]


def _write_history(history: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def delete_snapshot(index: int) -> None:
    """Elimina el snapshot en la posición `index` del historial."""
    history = load_history()
    if 0 <= index < len(history):
        history.pop(index)
        _write_history(history)


def move_snapshot(index: int, direction: int) -> None:
    """Mueve el snapshot en `index` una posición hacia arriba (-1) o abajo (+1)."""
    history = load_history()
    target = index + direction
    if 0 <= index < len(history) and 0 <= target < len(history):
        history[index], history[target] = history[target], history[index]
        _write_history(history)
