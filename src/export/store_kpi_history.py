from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

_SRC_PROCESSING_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_SRC_PROCESSING_DIR, "..", ".."))
HISTORY_PATH = os.path.join(_PROJECT_ROOT, "datasets", "kpi_history.json")


def _read_history(path: str) -> list[dict]:

    if not os.path.exists(path):
        logger.info("History file not found at '%s'. A new one will be created.", path)
        return []

    try:
        with open(path, "r", encoding="utf-8") as fh:
            content = fh.read().strip()

        if not content:
            logger.warning("History file '%s' is empty. Starting fresh.", path)
            return []

        data = json.loads(content)

        if not isinstance(data, list):
            raise ValueError(
                f"Expected a JSON array at the top level, got {type(data).__name__}."
            )

        logger.debug("Read %d existing record(s) from '%s'.", len(data), path)
        return data

    except json.JSONDecodeError as exc:
        logger.error(
            "History file '%s' contains invalid JSON (%s). "
            "A backup will be created and the file will be reset.",
            path,
            exc,
        )
        _backup_corrupted_file(path)
        return []

    except ValueError as exc:
        logger.error(
            "Unexpected format in '%s': %s. "
            "A backup will be created and the file will be reset.",
            path,
            exc,
        )
        _backup_corrupted_file(path)
        return []


def _backup_corrupted_file(path: str) -> None:

    timestamp_tag = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = f"{path}.corrupted.{timestamp_tag}.bak"
    try:
        os.rename(path, backup_path)
        logger.warning("Corrupted file backed up to '%s'.", backup_path)
    except OSError as exc:
        logger.error(
            "Could not back up corrupted file '%s': %s. Proceeding without backup.",
            path,
            exc,
        )


def _write_history(path: str, records: list[dict]) -> None:

    dir_path = os.path.dirname(path)
    os.makedirs(dir_path, exist_ok=True)

    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(records, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp_path, path)
        logger.info("History written to '%s' (%d record(s) total).", path, len(records))
    except OSError:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
        raise


def _enrich_record(record: dict[str, Any]) -> dict[str, Any]:

    enriched = dict(record)
    enriched.setdefault(
        "stored_at",
        datetime.now(timezone.utc).isoformat(),
    )
    return enriched


def store_kpi_history(
    record: dict[str, Any],
    path: str = HISTORY_PATH,
) -> list[dict]:
    
    if not isinstance(record, dict):
        raise TypeError(
            f"'record' must be a dict, got {type(record).__name__}."
        )

    existing = _read_history(path)
    enriched = _enrich_record(record)
    existing.append(enriched)
    _write_history(path, existing)

    logger.info(
        "KPI record for project '%s' (timestamp: %s) appended to history "
        "(%d record(s) now stored).",
        enriched.get("project", "unknown"),
        enriched.get("timestamp", "n/a"),
        len(existing),
    )

    return existing

if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    try:
        from kpi_model import load_weights, load_normalization_config
        from normalize_metrics import normalize_metrics
        from calculate_kpis import build_dataset, calculate_kpi
    except ImportError as e:
        logger.error(
            "Could not import project modules: %s\n"
            "Run this script from the src/processing/ directory or set "
            "PYTHONPATH accordingly.",
            e,
        )
        sys.exit(1)

    sonar_path = os.path.join(_PROJECT_ROOT, "data", "raw", "sonar_metrics.json")
    try:
        with open(sonar_path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        logger.error("SonarQube metrics file not found at '%s'.", sonar_path)
        sys.exit(1)

    weights     = load_weights()
    caps, defaults = load_normalization_config()
    normalized  = normalize_metrics(data["metrics"], caps=caps, defaults=defaults)
    kpi_score   = calculate_kpi(normalized, weights)
    record      = build_dataset(data, normalized, kpi_score, weights)

    history     = store_kpi_history(record)

    print(f"\nKPI history now contains {len(history)} record(s).")
    print(f"Latest entry stored at: {history[-1].get('stored_at')}")
    print(f"KPI score: {history[-1].get('kpi_score')} / 10")