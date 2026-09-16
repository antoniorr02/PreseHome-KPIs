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

Both commands above also run automatically on a schedule via `.github/workflows/main.yml` (issues #41/#42, US06) — see Automation below. Running them manually, as documented here, is for local development/testing; production runs happen through that workflow.

Individual modules (`src/export/store_kpi_history.py`, `src/export/write_influx.py`, `src/processing/normalize_metrics.py`, `src/processing/kpi_model.py`, `src/utils/onedrive/onedrive_client.py`, `src/utils/onedrive/upload_onedrive.py`, `src/utils/powerbi/export_history_csv.py`) each have a `__main__` block for standalone testing, runnable directly from the repo root (e.g. `python src/export/write_influx.py`) with no manual `PYTHONPATH`/`cd` setup — see Import wiring below.

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
- `src/utils/powerbi/export_history_csv.py` — flattens `datasets/kpi_history.json` into `data/processed/kpi_history_flat.csv`. Exists because the Power BI executive report (issue #38) was built via a one-time local file upload to Power BI Service (no Power BI Desktop on Linux, so no Power Query available) and has no live refresh — see README.md's "Keeping the Power BI Report Up to Date" section for the full manual refresh procedure this script is one step of.

**Dashboards (US05, issues #37/#38):** `dashboards/grafana/code_quality_dashboard.json` (exported Grafana dashboard, importable as-is) and `dashboards/powerbi/Executive Report - PreseHome.pbix` (built in Power BI Service's web editor, no Desktop involved). The Power BI report's DAX measures are documented in plain text at `docs/powerbi/dax_measures.md` — since DAX lives inside the `.pbix` binary, that file is the only place the measures are actually readable without opening Power BI. Dashboard screenshots (if present) live at `docs/screenshots/`.

**Automation (US06, issues #41/#42):** `.github/workflows/main.yml` runs `extract_sonar.py` → `calculate_kpis.py` daily (`cron`) plus on-demand (`workflow_dispatch`), with all credentials read from GitHub Actions repository secrets (see .env.example for the full variable list). A final step (`stefanzweifel/git-auto-commit-action`) commits any changed `data/raw/`, `data/processed/`, or `datasets/kpi_history.json` files back to the branch under a bot identity, so the schedule's output actually persists in the repo instead of vanishing with the ephemeral runner. GitHub only fires `schedule` triggers from the repository's default branch, so the cron doesn't run until this workflow is on `main`.

**Import wiring:** `src/`, `src/extraction/`, `src/processing/`, `src/export/`, `src/utils/`, `src/utils/onedrive/`, and `src/utils/powerbi/` are real Python packages (each has an `__init__.py`), and the project is installed in editable mode (`pip install -e .`, driven by `pyproject.toml` at the repo root — this is a required Setup step). Cross-directory imports use absolute, package-rooted paths, e.g. `calculate_kpis.py` (in `src/processing/`) does `from src.export.write_influx import write_kpi_to_influx`, and `write_influx.py`'s `__main__` does `from src.processing.kpi_model import load_weights`. There is no `sys.path` mutation anywhere in `src/` — the editable install is what makes `src.*` resolvable from any working directory or script location. If you add a new cross-directory import, use the same `from src.<dir>.<module> import ...` form; no path setup is needed beyond the one-time `pip install -e .`.

**Configuration:**
- `src/processing/config.json` — metric weights (must sum to ~1.0; `calculate_kpi` raises `InvalidWeightsError` if they don't, within a 0.99–1.01 tolerance), normalization caps, and missing-value defaults (the latter two loaded via `kpi_model.load_normalization_config()`).
- `.env` (see `.env.example`) — SonarCloud and InfluxDB v2 credentials, loaded via `python-dotenv`. Also holds `ONEDRIVE_*` credentials, but those are only read by the standalone `src/utils/onedrive/` utility (see Utilities above), not the active pipeline.

**Data flow directories:**
- `data/raw/` — raw SonarCloud extraction output (input to processing).
- `data/processed/` — latest KPI result as CSV/XLSX (overwritten each run, not historical).
- `datasets/kpi_history.json` — the append-only historical record (this is what Grafana/Power BI trend views are meant to read from over time).

## Current work

Issue #38 (Build Power BI executive KPI report) is done, but Power BI Desktop doesn't run on Linux, so the report was built entirely in Power BI Service's browser-based editor: `datasets/kpi_history.json` was flattened to CSV and uploaded directly (no live connection), and the DAX measures from the plan were added via Service's web "New measure"/"New table" UI rather than Desktop. This means the report has no live refresh — see README.md's "Keeping the Power BI Report Up to Date" for the manual process, and `src/utils/powerbi/export_history_csv.py` for the script that automates the flattening half of it.

US06 (issue #6) is in progress: #41 (scheduled GitHub Actions workflow) and #42 (commit pipeline outputs back to the repo) are both done — see Automation above. #43 (switch Power BI's data source to read directly from GitHub instead of the manual CSV upload) is not done yet; it depends on #41/#42 actually being live on `main` first (the cron trigger and the stable file URL Power BI needs both require that), which is the reason this branch was merged ahead of #43 being finished. Once #43 is verified working, four docs need updating to stop describing a manual process: README.md's "Keeping the Power BI Report Up to Date" section, this file's "no live refresh" line above, docs/architecture/architecture.md's Power BI note, and docs/powerbi/dax_measures.md's closing line. Don't update those preemptively — they're still accurate as written until #43 is actually confirmed working.
