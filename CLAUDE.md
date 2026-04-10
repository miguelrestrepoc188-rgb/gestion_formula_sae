# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Run the Streamlit app
streamlit run app.py
```

The app opens at `http://localhost:8501`. There are no tests or linters configured.

## Architecture Overview

KRATOS PM is a Streamlit project management tool for the EAFIT Kratos Formula SAE Electric Vehicle team. It ingests an Excel schedule, runs CPM analysis, and provides multiple project tracking views.

### Data Flow

```
Excel Upload ("Diseño a Detalle" sheet)
    ↓
core/data_cleaner.py  — normalize states, fix dates, parse predecessors,
                         flag quality issues, inject missing FSAE activities
    ↓
Cleaned DataFrame (stored in st.session_state["df"])
    ↓
core/cpm_engine.py    — topological sort, forward/backward pass,
                         slack calculation, critical path detection
    ↓
views/                — render selected view from sidebar navigation
```

### Key Modules

- **`app.py`** — Entry point. Manages session state, sidebar file upload, and routes to views.
- **`config.py`** — Central source of truth for the Kratos brand palette, CSS, state normalization mappings, and subsystem definitions. Edit here to change global styling or color.
- **`core/data_cleaner.py`** — Full Excel-to-DataFrame pipeline. `load_excel()` is the main entry point; it chains all normalization steps. Automatically injects ~15 placeholder activities for FSAE-required systems (Shutdown, BMS, Wire Harness, Technical Inspection, Competition Docs).
- **`core/cpm_engine.py`** — CPM implementation using `CPMEngine` class. Uses NetworkX for graph operations. `compute()` runs the full forward/backward pass; `get_critical_path_df()` and `get_full_schedule_df()` are the primary outputs consumed by views.

### Views

| File | Purpose |
|------|---------|
| `views/dashboard.py` | KPI summary, progress by microsubsystem, state distribution |
| `views/gantt.py` | Interactive Plotly Gantt (capped at 80 activities); critical path highlighted in `AMARILLO_NEON` |
| `views/cpm_view.py` | Float/slack analysis, multilevel subsystem filtering |
| `views/my_tasks.py` | Per-member task view with urgency color-coding |
| `views/task_editor.py` | CRUD for activities; tab 3 exports to JSON/CSV |
| `views/diagnostics.py` | Data quality scores, FSAE compliance checklist |

### State Management

All persistent data lives in `st.session_state`:
- `df` — cleaned DataFrame
- `cpm` — `CPMEngine` instance after `compute()` is called
- `uploaded_file_name` — display name of the loaded file

### Canonical Activity States

Defined in `config.py` (`ESTADO_MAPPING`); `data_cleaner.normalize_estados()` maps 9+ free-text variants to exactly four values: `no_iniciado`, `en_progreso`, `terminado`, `bloqueado`.

### Styling

All custom CSS is injected via `config.GLOBAL_CSS` using `st.markdown(..., unsafe_allow_html=True)`. The Kratos color palette (purple `#9E7AE1`, neon yellow `#DEFF5D`, dark background `#0E0E0E`) is defined as constants in `config.py` and referenced throughout views.
