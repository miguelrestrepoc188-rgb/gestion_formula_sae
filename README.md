# KRATOS PM — Plataforma de Gestión FSAE Eléctrico

Plataforma de gestión de proyecto para el equipo Kratos FSAE EV (Universidad EAFIT).  
Incluye visualización de ruta crítica (CPM), Gantt interactivo, dashboard de avance y editor de tareas.

## Requisitos

- Python 3.10+
- VS Code (recomendado)

## Instalación

```bash
# 1. Clonar o copiar el proyecto
cd kratos_pm

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt
```

## Ejecución

```bash
streamlit run app.py
```

Se abre automáticamente en `http://localhost:8501`

## Estructura del Proyecto

```
kratos_pm/
├── app.py                      # Punto de entrada Streamlit
├── config.py                   # Branding Kratos + constantes
├── requirements.txt
├── .streamlit/
│   └── config.toml             # Tema dark mode
├── core/
│   ├── data_cleaner.py         # Pipeline de limpieza Excel → DataFrame
│   └── cpm_engine.py           # Motor de Ruta Crítica (CPM)
├── views/
│   ├── dashboard.py            # Dashboard principal
│   ├── gantt.py                # Gantt interactivo
│   ├── cpm_view.py             # Análisis de ruta crítica
│   ├── my_tasks.py             # Panel de tareas personales
│   ├── task_editor.py          # CRUD de actividades
│   └── diagnostics.py          # Diagnóstico y compliance FSAE
├── data/
│   └── (aquí va el Excel)
└── README.md
```

## Uso

1. Abre la app con `streamlit run app.py`
2. En el panel lateral, sube el archivo `Cronograma_Detallado_de_Tareas.xlsx`
3. El sistema automáticamente:
   - Normaliza los 9 estados a 4 canónicos
   - Corrige fechas invertidas
   - Resuelve predecesores de texto a IDs
   - Agrega actividades críticas faltantes (Shutdown, BMS, Arnés, Documentación)
   - Calcula la ruta crítica (CPM)
4. Navega entre vistas usando el menú lateral

## Vistas

- **Dashboard**: KPIs, avance por subsistema, distribución de estados, timeline
- **Gantt**: Diagrama de Gantt filtrable con ruta crítica resaltada
- **Ruta Crítica**: Análisis CPM con mapa de holgura y filtro multinivel
- **Mis Tareas**: Vista personal por responsable con alertas de entregas próximas
- **Editor**: Agregar/modificar actividades con validación
- **Diagnóstico**: Reporte de calidad de datos y checklist FSAE 2026

## Exportar / Importar

Desde la pestaña Editor > Exportar:
- **JSON**: Formato nativo para backup y compartir
- **CSV**: Para análisis en Excel

## Notas Técnicas

- Los colores siguen la paleta del Manual de Marca Kratos 2026
- Tipografía: Poppins (cargada desde Google Fonts)
- El CPM engine maneja grafos con ciclos y nodos desconectados
- Las actividades placeholder se marcan con `is_placeholder=True`
