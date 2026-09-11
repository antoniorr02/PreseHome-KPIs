"""
onedrive_client.py
-------------------
Authenticates against Microsoft Graph API (OneDrive) using MSAL's
public-client device-code flow, and exposes a ready-to-use access token.

Required environment variables
-------------------------------
ONEDRIVE_CLIENT_ID   Application (client) ID from the Azure app registration
                      (Azure Portal → App registrations → your app → Overview).

Optional environment variables
-------------------------------
ONEDRIVE_TENANT            Azure AD tenant. Use "consumers" for personal
                            Microsoft accounts (default), "organizations" for
                            work/school accounts, or a specific tenant ID.
ONEDRIVE_TOKEN_CACHE_PATH  Path to the local MSAL token cache file
                            (default: <project root>/.onedrive_token_cache.json).
                            This file holds the refresh token — never commit it.

First run vs. later runs
-------------------------
get_access_token() first tries a silent, cached token refresh. If there is
no cached account yet (first run, or the refresh token expired), it falls
back to MSAL's device-code flow: a URL and one-time code are printed to the
console, you sign in with a browser once, and MSAL persists the resulting
refresh token to ONEDRIVE_TOKEN_CACHE_PATH. Every subsequent call reuses
that cached token silently — no browser, no manual step — for as long as
the refresh token stays valid.

Status
------
This module is NOT currently wired into the active pipeline — see
src/utils/onedrive/upload_onedrive.py's docstring and CLAUDE.md's
"Utilities" section for why, and how to use it manually.

Usage
-----
    from src.utils.onedrive.onedrive_client import (
        get_access_token, OneDriveConfigError, OneDriveAuthError,
    )

    try:
        token = get_access_token()
    except OneDriveConfigError as exc:
        # Missing/invalid env vars - abort early
        ...
    except OneDriveAuthError as exc:
        # Sign-in / token refresh failed
        ...
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import msal
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class OneDriveConfigError(Exception):
    """Raised when required environment variables are missing or invalid."""


class OneDriveAuthError(Exception):
    """Raised when device-code sign-in or silent token refresh fails."""


SCOPES = ["Files.ReadWrite"]

_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_DEFAULT_TOKEN_CACHE_PATH = os.path.join(_PROJECT_ROOT, ".onedrive_token_cache.json")


@dataclass(frozen=True)
class OneDriveConfig:
    client_id: str
    tenant: str
    token_cache_path: str


def load_onedrive_config() -> OneDriveConfig:
    client_id = os.getenv("ONEDRIVE_CLIENT_ID", "").strip()
    if not client_id:
        raise OneDriveConfigError(
            "ONEDRIVE_CLIENT_ID is missing or empty. Set it in your .env file "
            "to the Application (client) ID from your Azure app registration."
        )

    tenant = os.getenv("ONEDRIVE_TENANT", "").strip() or "consumers"
    token_cache_path = (
        os.getenv("ONEDRIVE_TOKEN_CACHE_PATH", "").strip() or _DEFAULT_TOKEN_CACHE_PATH
    )

    return OneDriveConfig(client_id=client_id, tenant=tenant, token_cache_path=token_cache_path)


def _load_cache(path: str) -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as fh:
            cache.deserialize(fh.read())
    return cache


def _save_cache(cache: msal.SerializableTokenCache, path: str) -> None:
    if not cache.has_state_changed:
        return
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(cache.serialize())
    try:
        os.chmod(path, 0o600)  # token cache holds a refresh token - keep it user-only
    except OSError:
        pass


def get_access_token() -> str:
    config = load_onedrive_config()

    cache = _load_cache(config.token_cache_path)
    app = msal.PublicClientApplication(
        client_id=config.client_id,
        authority=f"https://login.microsoftonline.com/{config.tenant}",
        token_cache=cache,
    )

    result = None
    accounts = app.get_accounts()
    if accounts:
        result = app.acquire_token_silent(SCOPES, account=accounts[0])

    if not result:
        flow = app.initiate_device_flow(scopes=SCOPES)
        if "user_code" not in flow:
            raise OneDriveAuthError(
                "Could not start device-code sign-in: "
                f"{flow.get('error_description', flow)}"
            )
        logger.info(flow["message"])
        print(flow["message"])
        result = app.acquire_token_by_device_flow(flow)

    _save_cache(cache, config.token_cache_path)

    if not result or "access_token" not in result:
        error = result.get("error") if result else "no_result"
        description = result.get("error_description") if result else "device flow returned nothing"
        raise OneDriveAuthError(f"Could not obtain an access token: {error}: {description}")

    return result["access_token"]


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    try:
        token = get_access_token()
        print(f"Access token acquired (first 12 chars): {token[:12]}...")
    except (OneDriveConfigError, OneDriveAuthError) as exc:
        logger.error("%s", exc)
        raise SystemExit(1)
