# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

PreseHome-KPIs is an engineering metrics pipeline: it pulls code quality data from SonarCloud, computes a single weighted KPI score (0–10), and fans the result out to three destinations — InfluxDB/Grafana (technical dashboards), Excel/Power BI (executive reporting), and a JSON history file (backup/trend log). See `README.md` for the full narrative and ASCII architecture diagram, and `docs/metrics/kpi_definition.md` for the KPI formula. There's also a standalone, unused-by-default OneDrive upload utility — see Utilities below.

## Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .        # installs the src package in editable mode (see Import wiring below)
cp .env.example .env    # then fill in SONAR_* and INFLUX_* values
```

There is no test suite and no linter configured in this repo.

## Commands

Run the pipeline in two stages:

```bash
python src/extraction/extract_sonar.py     # pulls bugs/vulnerabilities/code_smells/coverage from SonarCloud
                                            # → writes data/raw/sonar_metrics.json

python src/processing/calculate_kpis.py    # normalizes, weights, scores, and fans out (see below)
```

`calculate_kpis.py` is the single orchestrating entry point for stage 2. Running it does all of the following in one pass: normalize raw metrics → compute the weighted KPI (raises `InvalidWeightsError` if `config.json`'s weights don't sum to ~1.0, see Configuration below) → write `data/processed/kpi_results.csv` and `.xlsx` → append a record to `datasets/kpi_history.json` → write a point to InfluxDB (a write failure here is caught and only logged as a warning — the rest of the pipeline still succeeds).

Individual modules (`src/export/store_kpi_history.py`, `src/export/write_influx.py`, `src/processing/normalize_metrics.py`, `src/processing/kpi_model.py`, `src/utils/onedrive/onedrive_client.py`, `src/utils/onedrive/upload_onedrive.py`) each have a `__main__` block for standalone testing, runnable directly from the repo root (e.g. `python src/export/write_influx.py`) with no manual `PYTHONPATH`/`cd` setup — see Import wiring below.

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

**Utilities (not wired into the active pipeline):**
- `src/utils/onedrive/` — a working, documented, standalone OneDrive upload utility, built for issue #28. It is deliberately **not** called from `calculate_kpis.py`: Power BI's data source is now planned to read directly from this GitHub repo instead (see the follow-up issue for that switch), so this utility exists as an available integration rather than an active one. Kept because it's a complete, correct implementation worth having on hand (and demonstrating).
  - `onedrive_client.py` — authenticates against Microsoft Graph via MSAL's public-client device-code flow (personal Microsoft account, no client secret). First run requires an interactive one-time sign-in (prints a URL + code to the console); the resulting refresh token is cached at `ONEDRIVE_TOKEN_CACHE_PATH` (default `.onedrive_token_cache.json`, gitignored) and reused silently on every later run.
  - `upload_onedrive.py` — uploads a local file to a fixed OneDrive folder (`ONEDRIVE_TARGET_FOLDER`, default `/PreseHome-KPIs`) via Graph's simple-upload endpoint, which overwrites the existing file each run. Validates the file extension (`.csv`/`.xlsx` only) before attempting auth; retries transient failures, does not retry 401/403.
  - To use it: set `ONEDRIVE_CLIENT_ID` (and optionally `ONEDRIVE_TENANT`/`ONEDRIVE_TARGET_FOLDER`) in `.env`, then `python src/utils/onedrive/upload_onedrive.py` (uploads `data/processed/kpi_results.csv`/`.xlsx`) or `from src.utils.onedrive.upload_onedrive import upload_to_onedrive` from anywhere else. Requires the one-time Azure app registration described in that module's docstring.

**Import wiring:** `src/`, `src/extraction/`, `src/processing/`, `src/export/`, `src/utils/`, and `src/utils/onedrive/` are real Python packages (each has an `__init__.py`), and the project is installed in editable mode (`pip install -e .`, driven by `pyproject.toml` at the repo root — this is a required Setup step). Cross-directory imports use absolute, package-rooted paths, e.g. `calculate_kpis.py` (in `src/processing/`) does `from src.export.write_influx import write_kpi_to_influx`, and `write_influx.py`'s `__main__` does `from src.processing.kpi_model import load_weights`. There is no `sys.path` mutation anywhere in `src/` — the editable install is what makes `src.*` resolvable from any working directory or script location. If you add a new cross-directory import, use the same `from src.<dir>.<module> import ...` form; no path setup is needed beyond the one-time `pip install -e .`.

**Configuration:**
- `src/processing/config.json` — metric weights (must sum to ~1.0; `calculate_kpi` raises `InvalidWeightsError` if they don't, within a 0.99–1.01 tolerance), normalization caps, and missing-value defaults (the latter two loaded via `kpi_model.load_normalization_config()`).
- `.env` (see `.env.example`) — SonarCloud and InfluxDB v2 credentials, loaded via `python-dotenv`. Also holds `ONEDRIVE_*` credentials, but those are only read by the standalone `src/utils/onedrive/` utility (see Utilities above), not the active pipeline.

**Data flow directories:**
- `data/raw/` — raw SonarCloud extraction output (input to processing).
- `data/processed/` — latest KPI result as CSV/XLSX (overwritten each run, not historical).
- `datasets/kpi_history.json` — the append-only historical record (this is what Grafana/Power BI trend views are meant to read from over time).

## Current work

The repo is mid-refactor (branch `feature/us04-store-kpi-history`, tracking backlog item US04): `influx_client.py` and `store_kpi_history.py` moved from `src/processing/` to `src/export/`, and `write_influx.py` is new. That move is complete, and the cross-directory imports it required are now handled by the package structure described in Import wiring above (no more per-file `sys.path` insertion needed).

Issue #28 (upload KPI files to OneDrive for Power BI) was implemented in full (`src/utils/onedrive/onedrive_client.py` + `upload_onedrive.py` — auth, upload, retry, validation, logging all present and manually verified except the live device-code sign-in, which needs a real Azure app registration to exercise). It was then deliberately unwired from the active pipeline: Power BI's data source is now planned to read directly from this GitHub repo instead of OneDrive (avoids the Azure AD tenant-provisioning friction personal Microsoft accounts can hit, and reuses the repo access GitHub Actions will already have for US06). The OneDrive code was kept as a standalone utility rather than deleted — see Utilities above. The GitHub-as-data-source switch is tracked as a follow-up issue, not yet filed as of this note.
