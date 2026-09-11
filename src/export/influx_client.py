"""
influx_client.py
----------------
Initializes and validates the InfluxDB v2 client from environment variables.
 
Required environment variables
-------------------------------
INFLUX_URL       Full URL of the InfluxDB instance
                 e.g. https://eu-central-1-1.aws.cloud2.influxdata.com
INFLUX_TOKEN     API token with write access to the target bucket
INFLUX_ORG       Organisation name or ID
INFLUX_BUCKET    Destination bucket where KPI points are written
 
Optional environment variables
-------------------------------
INFLUX_TIMEOUT   Request timeout in milliseconds (default: 10 000)
 
Usage
-----
    from influx_client import get_influx_client, InfluxConfigError
 
    try:
        client, write_api = get_influx_client()
    except InfluxConfigError as exc:
        # Missing / invalid env vars – abort early
        ...
    except InfluxConnectionError as exc:
        # Credentials OK but server unreachable – handle gracefully
        ...
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class InfluxConfigError(Exception):
    """Raised when one or more required environment variables are missing
    or clearly invalid before any network call is attempted."""


class InfluxConnectionError(Exception):
    """Raised when the client can be constructed but the server is
    unreachable or rejects the credentials."""


@dataclass(frozen=True)
class InfluxConfig:
    url:     str
    token:   str
    org:     str
    bucket:  str
    timeout: int


_REQUIRED_VARS: tuple[str, ...] = (
    "INFLUX_URL",
    "INFLUX_TOKEN",
    "INFLUX_ORG",
    "INFLUX_BUCKET",
)

_DEFAULT_TIMEOUT_MS = 10000


def _collect_env() -> dict[str, str | None]:
    return {var: os.getenv(var) for var in _REQUIRED_VARS}


def _validate_env(env: dict[str, str | None]) -> None:
    missing = [var for var, val in env.items() if not val or not val.strip()]
    if missing:
        raise InfluxConfigError(
            "The following required environment variables are missing or empty: "
            + ", ".join(missing)
            + ". Set them in your .env file or CI/CD secrets."
        )


def _parse_timeout() -> int:
    raw = os.getenv("INFLUX_TIMEOUT", "").strip()
    if not raw:
        return _DEFAULT_TIMEOUT_MS
    try:
        value = int(raw)
        if value <= 0:
            raise ValueError("Timeout must be a positive integer.")
        return value
    except ValueError:
        logger.warning(
            "INFLUX_TIMEOUT='%s' is not a valid positive integer. "
            "Using default %d ms.",
            raw,
            _DEFAULT_TIMEOUT_MS,
        )
        return _DEFAULT_TIMEOUT_MS


def load_influx_config() -> InfluxConfig:
    env = _collect_env()
    _validate_env(env)

    config = InfluxConfig(
        url=env["INFLUX_URL"].strip(),
        token=env["INFLUX_TOKEN"].strip(),
        org=env["INFLUX_ORG"].strip(),
        bucket=env["INFLUX_BUCKET"].strip(),
        timeout=_parse_timeout(),
    )

    logger.debug(
        "InfluxDB config loaded → url=%s  org=%s  bucket=%s  timeout=%d ms",
        config.url,
        config.org,
        config.bucket,
        config.timeout,
    )
    return config


def get_influx_client():
    # Late import so the rest of the module is importable even when
    # influxdb-client is not installed (useful for unit testing with mocks).
    try:
        from influxdb_client import InfluxDBClient
        from influxdb_client.client.exceptions import InfluxDBError
        from influxdb_client.client.write_api import SYNCHRONOUS
    except ImportError as exc:
        raise ImportError(
            "influxdb-client is not installed. "
            "Run: pip install influxdb-client"
        ) from exc

    config = load_influx_config()

    try:
        client = InfluxDBClient(
            url=config.url,
            token=config.token,
            org=config.org,
            timeout=config.timeout,
        )

        if not client.ping():
            raise InfluxConnectionError(
                f"InfluxDB server at '{config.url}' did not respond to ping. "
                "Check that the URL is correct and the server is running."
            )

        logger.info(
            "InfluxDB connection established → %s (org=%s, bucket=%s)",
            config.url,
            config.org,
            config.bucket,
        )

        write_api = client.write_api(write_options=SYNCHRONOUS)
        return client, write_api

    except InfluxDBError as exc:
        raise InfluxConnectionError(
            f"InfluxDB rejected the request: {exc}"
        ) from exc

    except Exception as exc:
        # Catches urllib3 / socket errors (DNS failure, connection refused, TLS …)
        if isinstance(exc, (InfluxConfigError, InfluxConnectionError)):
            raise
        raise InfluxConnectionError(
            f"Could not reach InfluxDB at '{config.url}': {exc}"
        ) from exc


def get_bucket() -> str:
    config = load_influx_config()
    return config.bucket


if __name__ == "__main__":
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    try:
        client, write_api = get_influx_client()
        print("Connection successful.")
        client.close()
        sys.exit(0)
    except InfluxConfigError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(2)
    except InfluxConnectionError as exc:
        logger.error("Connection error: %s", exc)
        sys.exit(1)
