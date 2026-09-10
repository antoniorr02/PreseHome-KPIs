"""
write_influx.py
---------------
Writes a KPI record into InfluxDB as a time-series data point.

Data-point design
-----------------
measurement : "kpi_metrics"

tags   (indexed, used for filtering / grouping in Grafana)
  project               str   e.g. "PreseHome"

fields (numeric values stored as floats)
  kpi_score             final weighted score  0–10
  raw_bugs              raw SonarQube count
  raw_vulnerabilities   raw SonarQube count
  raw_code_smells       raw SonarQube count
  raw_coverage          raw SonarQube percentage
  norm_bugs             normalised score 0–10
  norm_vulnerabilities  normalised score 0–10
  norm_code_smells      normalised score 0–10
  norm_coverage         normalised score 0–10
  weight_bugs           weight applied (0–1)
  weight_vulnerabilities
  weight_code_smells
  weight_coverage

timestamp : ISO-8601 string taken from the record's "timestamp" field
            (the SonarQube extraction moment), converted to a
            datetime with UTC timezone so InfluxDB stores it correctly.

Public API
----------
    from write_influx import write_kpi_to_influx

    write_kpi_to_influx(record)           # uses env-var config
    write_kpi_to_influx(record, retries=5, retry_delay=2.0)
"""

from __future__ import annotations

import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

# Ensure src/export is on the path so influx_client is importable whether
# this module is run directly or imported from src/processing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from influx_client import (
        get_influx_client,
        load_influx_config,
        InfluxConfigError,
        InfluxConnectionError,
    )
    from influxdb_client.client.exceptions import InfluxDBError
except ImportError:
    # Deferred: will raise a clear ImportError at call time if influx_client
    # or influxdb-client is not on the path (e.g. during isolated unit tests).
    get_influx_client  = None
    load_influx_config = None
    InfluxConfigError  = Exception
    InfluxConnectionError = Exception
    InfluxDBError      = Exception

logger = logging.getLogger(__name__)

MEASUREMENT = "kpi_metrics"

_REQUIRED_FIELDS: tuple[str, ...] = (
    "kpi_score",
    "raw_bugs",
    "raw_vulnerabilities",
    "raw_code_smells",
    "raw_coverage",
    "norm_bugs",
    "norm_vulnerabilities",
    "norm_code_smells",
    "norm_coverage",
    "weight_bugs",
    "weight_vulnerabilities",
    "weight_code_smells",
    "weight_coverage",
)

_DEFAULT_RETRIES     = 3
_DEFAULT_RETRY_DELAY = 2.0

def _parse_timestamp(raw: str) -> datetime:
    if not raw:
        logger.warning(
            "Record has no 'timestamp' field. Using current UTC time."
        )
        return datetime.now(timezone.utc)

    try:
        # Python 3.11+ handles Z natively; for 3.9/3.10 we replace it first.
        normalised = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalised)
        if dt.tzinfo is None:
            logger.warning(
                "Timestamp '%s' has no timezone info – assuming UTC.", raw
            )
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        logger.warning(
            "Could not parse timestamp '%s'. Using current UTC time.", raw
        )
        return datetime.now(timezone.utc)


def _build_point(record: dict[str, Any]):
    from influxdb_client import Point  # late import (same pattern as influx_client.py)

    project = record.get("project")
    if not project:
        raise KeyError(
            "'project' key is missing or empty in the KPI record. "
            "It is required as an InfluxDB tag."
        )

    fields: dict[str, float] = {}
    missing, invalid = [], []
    for field in _REQUIRED_FIELDS:
        if field not in record:
            missing.append(field)
            continue
        try:
            fields[field] = float(record[field])
        except (TypeError, ValueError):
            invalid.append(f"{field}={record[field]!r}")

    if missing or invalid:
        parts = []
        if missing:
            parts.append(f"missing fields: {missing}")
        if invalid:
            parts.append(f"non-numeric fields: {invalid}")
        raise ValueError(
            "Cannot build InfluxDB point – " + "; ".join(parts) + "."
        )

    timestamp = _parse_timestamp(record.get("timestamp", ""))

    point = (
        Point(MEASUREMENT)
        .tag("project", project)
        .time(timestamp)
    )
    for field_name, field_value in fields.items():
        point = point.field(field_name, field_value)

    return point


def _attempt_write(write_api, bucket: str, org: str, point) -> None:
    """Execute a single write attempt (no retry here)."""
    write_api.write(bucket=bucket, org=org, record=point)


def write_kpi_to_influx(
    record: dict[str, Any],
    retries: int = _DEFAULT_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
) -> None:

    if not isinstance(record, dict):
        raise TypeError(
            f"'record' must be a dict, got {type(record).__name__}."
        )

    point = _build_point(record)

    try:
        client, write_api = get_influx_client()
    except InfluxConfigError:
        raise

    config = load_influx_config()

    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            _attempt_write(write_api, config.bucket, config.org, point)

            logger.info(
                "KPI point written to InfluxDB → measurement=%s  "
                "project=%s  timestamp=%s  kpi_score=%s  (attempt %d/%d)",
                MEASUREMENT,
                record.get("project"),
                record.get("timestamp"),
                record.get("kpi_score"),
                attempt,
                retries,
            )
            client.close()
            return

        except InfluxDBError as exc:
            last_exc = exc
            # 401 / 403 are auth errors – retrying won't help
            status = getattr(exc, "status", None) or getattr(exc, "response", {})
            if hasattr(status, "status") :
                status = status.status
            if str(status) in ("401", "403"):
                client.close()
                raise InfluxConnectionError(
                    f"InfluxDB rejected the write (HTTP {status}): {exc}. "
                    "Check INFLUX_TOKEN and bucket permissions."
                ) from exc

            logger.warning(
                "Write attempt %d/%d failed with InfluxDBError: %s",
                attempt, retries, exc,
            )

        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Write attempt %d/%d failed: %s", attempt, retries, exc
            )

        if attempt < retries:
            logger.info("Retrying in %.1f s…", retry_delay)
            time.sleep(retry_delay)

    client.close()
    raise InfluxConnectionError(
        f"Failed to write KPI point to InfluxDB after {retries} attempt(s). "
        f"Last error: {last_exc}"
    ) from last_exc


if __name__ == "__main__":
    import json
    import sys
    import os

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    _HERE        = os.path.dirname(os.path.abspath(__file__))
    _PROJECT_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
    sys.path.insert(0, os.path.join(_PROJECT_ROOT, "src", "processing"))

    sonar_path = os.path.join(_PROJECT_ROOT, "data", "raw", "sonar_metrics.json")
    try:
        with open(sonar_path) as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error("SonarQube metrics file not found at '%s'.", sonar_path)
        sys.exit(1)

    from kpi_model import load_weights, load_normalization_config
    from normalize_metrics import normalize_metrics
    from calculate_kpis import build_dataset, calculate_kpi

    weights    = load_weights()
    caps, defaults = load_normalization_config()
    normalized = normalize_metrics(data["metrics"], caps=caps, defaults=defaults)
    kpi_score  = calculate_kpi(normalized, weights)
    record     = build_dataset(data, normalized, kpi_score, weights)

    try:
        write_kpi_to_influx(record)
        print("Write successful.")
        sys.exit(0)
    except Exception as exc:
        logger.error("%s", exc)
        sys.exit(1)
