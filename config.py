"""
Configuración global y constantes de branding Kratos FSAE.
Paleta extraída del Manual de Marca 2026.
"""

# ── Paleta Kratos ──────────────────────────────────────────────
MORADO_OSCURO = "#2E0172"
LILA = "#9E7AE1"
AMARILLO_NEON = "#DEFF5D"
AZUL_OSCURO = "#061651"
AZUL_ELECTRICO = "#0D34E9"
BLANCO = "#FFFFFF"
NEGRO = "#000000"
BG_PRIMARY = "#0A0A0F"
BG_SECONDARY = "#12121A"
BG_CARD = "#1A1A2E"
BORDER_SUBTLE = "#2A2A3E"
TEXT_MUTED = "#8888AA"

# Colores semánticos
COLOR_OK = "#22C55E"
COLOR_WARNING = "#FACC15"
COLOR_DANGER = "#EF4444"
COLOR_INFO = LILA
COLOR_CRITICAL_PATH = AMARILLO_NEON

# ── Estados normalizados ───────────────────────────────────────
ESTADOS_VALIDOS = ["no_iniciado", "en_progreso", "terminado", "bloqueado"]

ESTADO_DISPLAY = {
    "no_iniciado": "No Iniciado",
    "en_progreso": "En Progreso",
    "terminado": "Terminado",
    "bloqueado": "Bloqueado",
}

ESTADO_COLOR = {
    "no_iniciado": TEXT_MUTED,
    "en_progreso": AZUL_ELECTRICO,
    "terminado": COLOR_OK,
    "bloqueado": COLOR_DANGER,
}

ESTADO_ICON = {
    "no_iniciado": "⏳",
    "en_progreso": "🔧",
    "terminado": "✅",
    "bloqueado": "🚫",
}

# ── Mapeo de normalización de estados del Excel original ───────
ESTADO_NORMALIZATION = {
    "no iniciado": "no_iniciado",
    "en progreso": "en_progreso",
    "en progreso ": "en_progreso",
    "terminado": "terminado",
    "terminado ": "terminado",
    "terminando": "terminado",
    "termiando": "terminado",
    "finalizado": "terminado",
    "finalizado ": "terminado",
    "iniciado": "en_progreso",
}

# ── Subsistemas y Microsubsistemas ─────────────────────────────
SUBSISTEMAS = {
    "DYM": {
        "nombre": "Dinámica y Mecánica",
        "color": LILA,
        "microsubsistemas": [
            "Aerodinámica", "Chasis", "Dirección",
            "Frenos", "Suspensión", "Transmisión"
        ],
    },
    "Electrónica": {
        "nombre": "Electrónica",
        "color": AMARILLO_NEON,
        "microsubsistemas": [
            "Batería", "Potencia", "Telemetría"
        ],
    },
}

# ── Fases del ciclo de vida ────────────────────────────────────
FASES = ["diseño", "manufactura", "pruebas"]

FASE_COLOR = {
    "diseño": LILA,
    "manufactura": AZUL_ELECTRICO,
    "pruebas": AMARILLO_NEON,
}

# ── CSS global para Streamlit ──────────────────────────────────
GLOBAL_CSS = f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Reset y base ── */
    html, body, .stApp {{
        font-family: 'Poppins', sans-serif !important;
        background-color: {BG_PRIMARY} !important;
        color: {BLANCO} !important;
    }}

    /* ── Sidebar ── */
    section[data-testid="stSidebar"] {{
        background-color: {BG_SECONDARY} !important;
        border-right: 1px solid {BORDER_SUBTLE} !important;
    }}
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li {{
        color: {BLANCO} !important;
    }}

    /* ── Headers ── */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Poppins', sans-serif !important;
        font-weight: 700 !important;
    }}
    h1 {{ color: {BLANCO} !important; }}
    h2 {{ color: {LILA} !important; }}
    h3 {{ color: {AMARILLO_NEON} !important; }}

    /* ── Metric cards ── */
    div[data-testid="stMetric"] {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER_SUBTLE} !important;
        border-radius: 12px !important;
        padding: 16px 20px !important;
    }}
    div[data-testid="stMetric"] label {{
        color: {TEXT_MUTED} !important;
        font-size: 0.8rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
    }}
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {{
        color: {BLANCO} !important;
        font-weight: 800 !important;
    }}

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 8px;
        background-color: transparent;
    }}
    .stTabs [data-baseweb="tab"] {{
        background-color: {BG_CARD};
        border-radius: 8px;
        color: {TEXT_MUTED};
        border: 1px solid {BORDER_SUBTLE};
        padding: 8px 20px;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {MORADO_OSCURO} !important;
        color: {BLANCO} !important;
        border-color: {LILA} !important;
    }}

    /* ── DataFrames ── */
    .stDataFrame {{
        border: 1px solid {BORDER_SUBTLE} !important;
        border-radius: 8px !important;
    }}

    /* ── Buttons ── */
    .stButton > button {{
        background-color: {MORADO_OSCURO} !important;
        color: {BLANCO} !important;
        border: 1px solid {LILA} !important;
        border-radius: 8px !important;
        font-family: 'Poppins', sans-serif !important;
        font-weight: 600 !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover {{
        background-color: {LILA} !important;
        color: {NEGRO} !important;
    }}

    /* ── Selectbox / inputs ── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div,
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stDateInput > div > div > input {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER_SUBTLE} !important;
        color: {BLANCO} !important;
        border-radius: 8px !important;
    }}

    /* ── Progress bars ── */
    .stProgress > div > div > div {{
        background-color: {LILA} !important;
    }}

    /* ── Expander ── */
    .streamlit-expanderHeader {{
        background-color: {BG_CARD} !important;
        border: 1px solid {BORDER_SUBTLE} !important;
        border-radius: 8px !important;
        color: {BLANCO} !important;
    }}

    /* ── Custom badge styles ── */
    .badge-ok {{ background: {COLOR_OK}22; color: {COLOR_OK}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
    .badge-warn {{ background: {COLOR_WARNING}22; color: {COLOR_WARNING}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
    .badge-danger {{ background: {COLOR_DANGER}22; color: {COLOR_DANGER}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
    .badge-info {{ background: {LILA}22; color: {LILA}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}
    .badge-critical {{ background: {AMARILLO_NEON}22; color: {AMARILLO_NEON}; padding: 2px 10px; border-radius: 12px; font-size: 0.75rem; font-weight: 600; }}

    /* ── Logo area ── */
    .kratos-header {{
        display: flex;
        align-items: center;
        gap: 16px;
        padding: 10px 0 20px 0;
    }}
    .kratos-logo {{
        font-family: 'Poppins', sans-serif;
        font-weight: 900;
        font-size: 2rem;
        letter-spacing: 0.08em;
    }}
    .kratos-logo .k-accent {{ color: {LILA}; }}
    .kratos-logo .k-rest {{ color: {BLANCO}; }}
    .kratos-subtitle {{
        color: {TEXT_MUTED};
        font-size: 0.8rem;
        letter-spacing: 0.15em;
        text-transform: uppercase;
    }}
</style>
"""
