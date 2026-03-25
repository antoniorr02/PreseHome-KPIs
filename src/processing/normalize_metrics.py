"""
Normalization rules
-------------------
Metric          Direction   Logic
-----------     ---------   -----------------------------------------------
bugs            Lower=Better  Capped at MAX_BUGS.  0 bugs → 10, MAX → 0.
vulnerabilities Lower=Better  Capped at MAX_VULN.  0 vuln → 10, MAX → 0.
code_smells     Lower=Better  Capped at MAX_SMELLS. 0 → 10, MAX → 0.
coverage        Higher=Better Direct mapping.       100 % → 10, 0 % → 0.

Missing-value policy
--------------------
- coverage   : defaults to 0.0  (worst case – penalises absence of tests)
- bugs       : defaults to 0    (absence of data ≠ presence of bugs)
- vulnerabilities: defaults to 0
- code_smells: defaults to 0

All defaults are documented in DEFAULT_VALUES and can be overridden via
the config.json that already drives the weight configuration.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Normalisation caps  (tune these in config.json → "normalization_caps")
# ---------------------------------------------------------------------------
DEFAULT_CAPS: dict[str, float] = {
    "bugs": 100.0,
    "vulnerabilities": 50.0,
    "code_smells": 500.0,
}

# ---------------------------------------------------------------------------
# Missing-value defaults
# ---------------------------------------------------------------------------
DEFAULT_VALUES: dict[str, float] = {
    "bugs": 0.0,
    "vulnerabilities": 0.0,
    "code_smells": 0.0,
    "coverage": 0.0,
}

def _clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    """Ensure a value stays within [low, high]."""
    return max(low, min(high, value))


def _normalize_lower_is_better(raw: float, cap: float) -> float:
    if cap <= 0:
        raise ValueError(f"Cap must be > 0, got {cap}")
    score = (1.0 - raw / cap) * 10.0
    return _clamp(score)


def _normalize_higher_is_better(raw: float, max_value: float = 100.0) -> float:
    if max_value <= 0:
        raise ValueError(f"max_value must be > 0, got {max_value}")
    score = (raw / max_value) * 10.0
    return _clamp(score)

def resolve_raw_metrics(
    raw_metrics: dict[str, Any],
    defaults: dict[str, float] | None = None,
) -> dict[str, float]:
    effective_defaults = {**DEFAULT_VALUES, **(defaults or {})}
    resolved: dict[str, float] = {}

    for metric, default in effective_defaults.items():
        raw_value = raw_metrics.get(metric)

        if raw_value is None:
            logger.warning(
                "Metric '%s' is missing from SonarQube response – "
                "using default value %.2f",
                metric,
                default,
            )
            resolved[metric] = float(default)
        else:
            try:
                resolved[metric] = float(raw_value)
            except (TypeError, ValueError):
                logger.error(
                    "Metric '%s' has non-numeric value '%s' – "
                    "falling back to default %.2f",
                    metric,
                    raw_value,
                    default,
                )
                resolved[metric] = float(default)

    return resolved


def normalize_metrics(
    raw_metrics: dict[str, Any],
    caps: dict[str, float] | None = None,
    defaults: dict[str, float] | None = None,
) -> dict[str, float]:
    effective_caps = {**DEFAULT_CAPS, **(caps or {})}

    # Step 1 – fill missing values
    resolved = resolve_raw_metrics(raw_metrics, defaults)

    # Step 2 – apply normalization rule per metric
    normalized: dict[str, float] = {}

    # --- lower-is-better metrics ---
    for metric in ("bugs", "vulnerabilities", "code_smells"):
        cap = effective_caps[metric]
        normalized[metric] = _normalize_lower_is_better(resolved[metric], cap)
        logger.debug(
            "normalize %-20s raw=%-8.2f cap=%-8.2f → score=%.4f",
            metric, resolved[metric], cap, normalized[metric],
        )

    # --- higher-is-better metrics ---
    normalized["coverage"] = _normalize_higher_is_better(resolved["coverage"], 100.0)
    logger.debug(
        "normalize %-20s raw=%-8.2f             → score=%.4f",
        "coverage", resolved["coverage"], normalized["coverage"],
    )

    return normalized

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s | %(message)s")

    sample_raw = {
        "bugs": 12,
        "vulnerabilities": 3,
        "code_smells": 87,
        "coverage": 74.5,
    }

    print("\n=== Sample raw metrics ===")
    for k, v in sample_raw.items():
        print(f"  {k}: {v}")

    scores = normalize_metrics(sample_raw)

    print("\n=== Normalized scores (0–10) ===")
    for k, v in scores.items():
        print(f"  {k}: {v:.4f}")

    print("\n=== Missing coverage scenario ===")
    missing_coverage = {k: v for k, v in sample_raw.items() if k != "coverage"}
    scores_no_cov = normalize_metrics(missing_coverage)
    for k, v in scores_no_cov.items():
        print(f"  {k}: {v:.4f}")