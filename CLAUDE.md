# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

PreseHome-KPIs is an engineering metrics pipeline: it pulls code quality data from SonarCloud, computes a single weighted KPI score (0–10), and fans the result out to three destinations — InfluxDB/Grafana (technical dashboards), Excel/Power BI (executive reporting), and a JSON history file (backup/trend log). See `README.md` for the full narrative and ASCII architecture diagram, and `docs/metrics/kpi_definition.md` for the KPI formula.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then fill in SONAR_* and INFLUX_* values
```

There is no test suite and no linter configured in this repo.

## Commands

Run the pipeline in two stages:

```bash
python src/extraction/extract_sonar.py     # pulls bugs/vulnerabilities/code_smells/coverage from SonarCloud
                                            # → writes data/raw/sonar_metrics.json

python src/processing/calculate_kpis.py    # normalizes, weights, scores, and fans out (see below)
```

`calculate_kpis.py` is the single orchestrating entry point for stage 2. Running it does all of the following in one pass: normalize raw metrics → compute the weighted KPI → write `data/processed/kpi_results.csv` and `.xlsx` → append a record to `datasets/kpi_history.json` → write a point to InfluxDB (a write failure here is caught and only logged as a warning — the rest of the pipeline still succeeds).

Individual modules (`src/export/store_kpi_history.py`, `src/export/write_influx.py`, `src/processing/normalize_metrics.py`, `src/processing/kpi_model.py`) each have a `__main__` block for standalone testing, but they expect to be run with `src/processing` on `PYTHONPATH` (see Import wiring below) — running them directly from elsewhere will fail on import unless that path is set up first.

## Architecture

**Pipeline stages**, each a separate directory under `src/`:

1. `src/extraction/extract_sonar.py` — calls the SonarCloud API (`SONAR_URL`/`SONAR_TOKEN`/`SONAR_PROJECT_KEY` from `.env`), writes raw metrics to `data/raw/sonar_metrics.json`.
2. `src/processing/` — the KPI engine:
   - `normalize_metrics.py` — maps each raw metric to a 0–10 score. `bugs`/`vulnerabilities`/`code_smells` are lower-is-better (capped and inverted); `coverage` is higher-is-better (direct scale). Caps and missing-value defaults come from `config.json`, overridable by callers.
   - `kpi_model.py` — loads metric weights from `config.json`.
   - `calculate_kpis.py` — orchestrates: computes the weighted sum (`calculate_kpi`), assembles the full record (`build_dataset`, with raw/normalized/weight/score columns), writes CSV/XLSX, and calls into `src/export/` for history and InfluxDB.
3. `src/export/` — fan-out destinations:
   - `store_kpi_history.py` — appends the record to `datasets/kpi_history.json` (atomic write via temp file + `os.replace`; corrupted history files are backed up with a timestamped `.bak` suffix rather than overwritten).
   - `influx_client.py` — builds/validates an InfluxDB v2 client from `INFLUX_*` env vars (`InfluxConfigError` for bad config, `InfluxConnectionError` for unreachable/rejected).
   - `write_influx.py` — builds an InfluxDB `Point` (measurement `kpi_metrics`, tagged by `project`) from a record and writes it with retry logic; distinguishes auth errors (401/403, no retry) from transient failures (retried).

**Import wiring (non-obvious, read before editing any of these files):** `calculate_kpis.py` lives in `src/processing/` but imports `store_kpi_history` and `write_influx` from `src/export/` by inserting that directory into `sys.path` at import time — there is no package structure or relative imports tying these directories together. `write_influx.py` inserts its own directory onto `sys.path` for the same reason (to import `influx_client`). This means the two directories are mutually dependent at runtime despite not being Python packages; if you move or rename a module in either `src/processing/` or `src/export/`, grep for `sys.path.insert` and the corresponding `from X import` lines across both directories to keep the wiring intact.

**Configuration:**
- `src/processing/config.json` — metric weights (must sum to ~1.0; `calculate_kpi` only warns, doesn't fail, if they don't), normalization caps, and missing-value defaults.
- `.env` (see `.env.example`) — SonarCloud and InfluxDB v2 credentials, loaded via `python-dotenv`.

**Data flow directories:**
- `data/raw/` — raw SonarCloud extraction output (input to processing).
- `data/processed/` — latest KPI result as CSV/XLSX (overwritten each run, not historical).
- `datasets/kpi_history.json` — the append-only historical record (this is what Grafana/Power BI trend views are meant to read from over time).

## Current work

The repo is mid-refactor (branch `feature/us04-store-kpi-history`, tracking backlog item US04): `influx_client.py` and `store_kpi_history.py` are being moved from `src/processing/` to `src/export/`, and `write_influx.py` is new. When touching these files, double-check the `__main__` blocks and `sys.path` insertions still match each file's actual location — several of them still assume the pre-move layout (e.g. `store_kpi_history.py`'s `__main__` imports `kpi_model`/`normalize_metrics`/`calculate_kpis` with no path insertion, so it only works if invoked from `src/processing/`).
