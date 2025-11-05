# FloatChart – ARGO Ocean Intelligence Suite

FloatChart is a desktop-first toolkit for oceanographic exploration built around ARGO float observations. The repository combines two tightly-coupled applications:

1. **ARGO_CHATBOT** – an interactive assistant that translates natural-language questions into SQL, visualises results, and lets analysts explore floats on an embedded map.
2. **DATA_GENERATOR** – an incremental ETL utility that pulls new ARGO profiles from the Ifremer ERDDAP catalogue, loads them into PostgreSQL, and archives the ingested sample set locally.

Together they provide an end-to-end workflow: fetch the most recent observations, ingest them safely, and interrogate the dataset through a conversational UI with rich visual output.

---

## Repository Layout

| Path | Purpose |
|------|---------|
| `ARGO_CHATBOT/` | Tkinter GUI, Flask API, intent interpreter, visual components, and related assets for the FloatChat assistant. |
| `DATA_GENERATOR/` | Headless + GUI tooling to fetch ERDDAP data, update PostgreSQL, maintain a CSV archive, and track ingestion checkpoints. |
| `.gitignore` | Repository-wide ignores for local state, generated assets, and large data files. |
| `LICENSE` | MIT license covering the full project. |
| `README.md` | This document.

Each sub-folder may also contain its own README or configuration files for component-specific details.

---

## Key Capabilities

### ARGO_CHATBOT
- Natural-language query parsing via Groq LLM models with guardrails for ARGO-specific intents.
- Generated SQL with automatic verification and graceful guidance when queries are under-specified.
- Interactive Tkinter interface featuring chat history, an embedded `tkintermapview`, and high-contrast theme.
- Inline data visualisations (profiles, time-series, scatter plots, metrics) with export to CSV/XLSX/PNG/ZIP packages.
- Auxiliary Flask API (`api_server.py`) powering map searches, float profiles, and trajectory retrieval.

### DATA_GENERATOR
- Incremental downloader against the `ArgoFloats-synthetic-BGC` dataset using ERDDAP NetCDF endpoints (via `xarray` + `netCDF4`).
- Duplicate-safe PostgreSQL loader with staging tables and unique key checks on `(float_id, timestamp, pressure)`.
- Persistent CSV archive of newly inserted rows for offline review.
- Tkinter GUI (`gui.py`) offering one-click updates, progress feedback, and summary reporting.
- State tracking (`update_state.json`) so each run resumes from the last successful ingestion window.

---

## Getting Started

### 1. Prerequisites
- Python 3.10+ (tested with Python 3.11).
- PostgreSQL instance with an accessible database (defaults expect `argo_db`).
- Groq API credentials for intent parsing and summarisation.
- Optional: a virtual environment for each component.

### 2. Configure environments
Create a `.env` file in **both** `ARGO_CHATBOT/` and `DATA_GENERATOR/` (or point one to the other) with at minimum:

```
DATABASE_URL=postgresql+psycopg2://postgres:password@localhost:5432/argo_db
GROQ_API_KEY=your_groq_key
GROQ_MODEL_NAME=llama-3.1-70b-versatile
```

Adjust credentials, host, and model as needed. The chatbot requires the Groq entries; the data generator only needs `DATABASE_URL`.

Install dependencies per component:

```bash
cd ARGO_CHATBOT
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

cd ..\DATA_GENERATOR
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

*(The generator now relies on `xarray`/`netCDF4` alongside `pandas` and `sqlalchemy` for NetCDF ingestion.)*

### 3. Refresh the dataset
Run the GUI or call `update_manager.perform_update()` to download and load new ARGO observations.

```powershell
cd DATA_GENERATOR
.venv\Scripts\activate
python gui.py
```

The GUI displays progress, inserts new rows into PostgreSQL, appends to `full_argo_dataset.csv`, and updates `update_state.json` for incremental continuity.

For headless updates you can invoke:

```python
from update_manager import perform_update
perform_update()
```

### 4. Launch the explorer
Start the Flask API (optional when running from the GUI, which can spawn it automatically):

```powershell
cd ARGO_CHATBOT
.venv\Scripts\Activate
python api_server.py
```

Then launch the main chatbot UI:

```powershell
python app_gui.py
```

The assistant will read the latest database range, accept natural-language questions, and render maps/graphs accordingly. Use the “Inter Map” button for the dedicated trajectory explorer found in `map_window.py`.

---

## Data Flow Summary

1. **ERDDAP → DATA_GENERATOR** – Fetches NetCDF windows bounded by the last success timestamp.
2. **DATA_GENERATOR → PostgreSQL (`argo_data`)** – Deduplicated inserts using a staging table.
3. **PostgreSQL → ARGO_CHATBOT** – Queries via dynamically generated SQL tuned to the user intent.
4. **ARGO_CHATBOT → User** – Conversational summaries, map visualisation, downloadable artefacts.

A quick health check for database freshness is provided by `DATA_GENERATOR/check_db_max.py`.

---

## Development Guidelines

- Commit without generated data (`full_argo_dataset.csv`, archives) thanks to the root `.gitignore`.
- Prefer component-specific virtual environments; both folders include helper `.gitignore` entries to keep them out of version control.
- Log output such as `backend.log` or ERDDAP download logs remain local; delete before committing if accidentally staged.
- If you add new dependencies, update the relevant `requirements.txt` and document configuration changes here.

---

## Data Citation

**ARGO Float Data:**
These data were collected and made freely available by the International Argo Program and the national programs that contribute to it. (https://argo.ucsd.edu, https://www.ocean-ops.org). The Argo Program is part of the Global Ocean Observing System.

**Data Source:**
- Provider: Ifremer ERDDAP (Official ARGO Global Data Assembly Center)
- Dataset: ArgoFloats-synthetic-BGC
- Access: https://erddap.ifremer.fr/erddap/
- License: Public Domain - Free for all uses including commercial
- Updates: Near real-time (~24 hour latency)

For detailed information about the data source, see [`DATA_SOURCE_VERIFICATION_REPORT.md`](DATA_SOURCE_VERIFICATION_REPORT.md).

---

## License

This project is offered under the terms of the MIT License. See [`LICENSE`](LICENSE) for full text.

ARGO data is provided free of charge by the International Argo Program and carries no restrictions on use.
