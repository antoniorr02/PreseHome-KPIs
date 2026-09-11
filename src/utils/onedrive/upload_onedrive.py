"""
upload_onedrive.py
-------------------
Uploads a local file (CSV or XLSX) to OneDrive via the Microsoft Graph API,
so Power BI can consume it as a live data source.

Target directory structure
---------------------------
Files are uploaded to a fixed folder under the OneDrive root, configurable
via ONEDRIVE_TARGET_FOLDER (default "/PreseHome-KPIs"). Each file keeps its
original basename (e.g. "kpi_results.csv").

Overwrite behaviour
--------------------
Every upload replaces the file at that exact path — Graph's simple-upload
PUT endpoint overwrites existing content by default, there is no versioning.
This mirrors data/processed/'s own "latest snapshot, not historical"
semantics (see CLAUDE.md), so Power BI always reads the most recent run.

File size note
----------------
This uses Graph's simple-upload endpoint, which is limited to 4 MB per
file. kpi_results.csv/.xlsx are single-record snapshots (a few KB), so this
is not a practical constraint; a much larger export would need Graph's
chunked upload-session API instead.

Status
------
This module is NOT currently wired into the active pipeline
(src/processing/calculate_kpis.py). It was built for issue #28 and is kept
as a working, documented, standalone utility — Power BI's data source is
now planned to read directly from this GitHub repo instead of OneDrive.
See CLAUDE.md's "Utilities" section for details and how to use it manually.

Public API
----------
    from src.utils.onedrive.upload_onedrive import upload_to_onedrive

    upload_to_onedrive("data/processed/kpi_results.csv")
    upload_to_onedrive("data/processed/kpi_results.xlsx", retries=5, retry_delay=2.0)
"""

from __future__ import annotations

import logging
import os
import time

import requests

from src.utils.onedrive.onedrive_client import (
    get_access_token,
    OneDriveConfigError,
    OneDriveAuthError,
)

logger = logging.getLogger(__name__)

GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
ALLOWED_EXTENSIONS = (".csv", ".xlsx")

_DEFAULT_RETRIES = 3
_DEFAULT_RETRY_DELAY = 2.0
_UPLOAD_TIMEOUT_SECONDS = 30


class OneDriveUploadError(Exception):
    """Raised when a file could not be uploaded to OneDrive after retries."""


def _validate_file(file_path: str) -> None:
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: '{file_path}'.")

    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type '{ext}' for '{file_path}'. "
            f"Allowed types: {', '.join(ALLOWED_EXTENSIONS)}."
        )


def _target_folder() -> str:
    folder = os.getenv("ONEDRIVE_TARGET_FOLDER", "").strip() or "/PreseHome-KPIs"
    return "/" + folder.strip("/")


def upload_to_onedrive(
    file_path: str,
    retries: int = _DEFAULT_RETRIES,
    retry_delay: float = _DEFAULT_RETRY_DELAY,
) -> str:
    """Upload file_path to OneDrive, overwriting any existing file at the
    same path. Returns the remote OneDrive path on success."""

    _validate_file(file_path)

    filename = os.path.basename(file_path)
    remote_path = f"{_target_folder()}/{filename}"

    with open(file_path, "rb") as fh:
        data = fh.read()

    token = get_access_token()

    url = f"{GRAPH_BASE_URL}/me/drive/root:{remote_path}:/content"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/octet-stream",
    }

    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            response = requests.put(
                url, headers=headers, data=data, timeout=_UPLOAD_TIMEOUT_SECONDS
            )

            if response.status_code in (200, 201):
                logger.info(
                    "Uploaded '%s' → OneDrive:%s (attempt %d/%d)",
                    file_path, remote_path, attempt, retries,
                )
                return remote_path

            if response.status_code in (401, 403):
                # Auth/permission errors won't be fixed by retrying.
                raise OneDriveUploadError(
                    f"OneDrive rejected the upload (HTTP {response.status_code}): "
                    f"{response.text}. Check ONEDRIVE_CLIENT_ID permissions/consent."
                )

            last_exc = OneDriveUploadError(
                f"Upload failed (HTTP {response.status_code}): {response.text}"
            )
            logger.warning(
                "Upload attempt %d/%d failed with HTTP %d: %s",
                attempt, retries, response.status_code, response.text,
            )

        except requests.RequestException as exc:
            last_exc = exc
            logger.warning(
                "Upload attempt %d/%d failed: %s", attempt, retries, exc
            )

        if attempt < retries:
            logger.info("Retrying in %.1f s…", retry_delay)
            time.sleep(retry_delay)

    raise OneDriveUploadError(
        f"Failed to upload '{file_path}' to OneDrive after {retries} attempt(s). "
        f"Last error: {last_exc}"
    )


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    _PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    targets = [
        os.path.join(_PROJECT_ROOT, "data", "processed", "kpi_results.csv"),
        os.path.join(_PROJECT_ROOT, "data", "processed", "kpi_results.xlsx"),
    ]

    exit_code = 0
    for path in targets:
        try:
            remote = upload_to_onedrive(path)
            print(f"Uploaded '{path}' → OneDrive:{remote}")
        except (OneDriveConfigError, OneDriveAuthError, OneDriveUploadError,
                FileNotFoundError, ValueError) as exc:
            logger.error("%s", exc)
            exit_code = 1

    sys.exit(exit_code)
