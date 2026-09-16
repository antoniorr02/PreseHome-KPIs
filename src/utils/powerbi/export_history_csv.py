"""
export_history_csv.py
----------------------
Flattens datasets/kpi_history.json into a flat CSV
(data/processed/kpi_history_flat.csv), since Power BI Service's "Upload a
file" only accepts CSV/Excel, not raw JSON.

Status
------
Legacy. This was the first step of Power BI's original manual refresh
process (issue #38) — Power BI Service's "Upload a file" only accepts
CSV/Excel, so kpi_history.json had to be flattened before every manual
re-upload. That process is retired: Power BI now reads kpi_history.json
live from GitHub via Power BI Service's Web connector (issue #43), no
CSV or manual step involved. Kept as a convenience for flattening
history locally (e.g. for inspection, or testing without waiting on a
GitHub Actions run) — not part of the automated pipeline or the Power BI
refresh path anymore. See README.md's "Keeping the Power BI Report Up
to Date" for how the live refresh actually works now.

Public API
----------
    from src.utils.powerbi.export_history_csv import export_history_csv

    export_history_csv()                        # uses default paths
    export_history_csv(output_path="somewhere/else.csv")
"""

from __future__ import annotations

import json
import logging
import os

import pandas as pd

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
_DEFAULT_HISTORY_PATH = os.path.join(_PROJECT_ROOT, "datasets", "kpi_history.json")
_DEFAULT_OUTPUT_PATH = os.path.join(_PROJECT_ROOT, "data", "processed", "kpi_history_flat.csv")


def export_history_csv(
    history_path: str = _DEFAULT_HISTORY_PATH,
    output_path: str = _DEFAULT_OUTPUT_PATH,
) -> str:
    with open(history_path, "r", encoding="utf-8") as fh:
        records = json.load(fh)

    if not records:
        raise ValueError(f"'{history_path}' has no records to export.")

    df = pd.DataFrame(records)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

    logger.info("Exported %d record(s) → %s", len(df), output_path)
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    try:
        path = export_history_csv()
        print(f"kpi_history.json flattened → {path}")
        print(
            "Next: upload this file to Power BI Service, replacing the "
            "existing dataset (same filename, same workspace) so your "
            "existing DAX measures and visuals carry over."
        )
    except (FileNotFoundError, ValueError) as exc:
        logging.error("%s", exc)
        sys.exit(1)
