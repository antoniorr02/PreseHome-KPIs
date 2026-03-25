# KPI Definition — Engineering Metrics Platform

## Purpose
Calculate a single weighted score (0–10) to evaluate overall application quality.

## Input Metrics
- Bugs
- Vulnerabilities
- Code Smells
- Coverage

## Weighting
- Bugs: 0.3
- Vulnerabilities: 0.3
- Code Smells: 0.2
- Coverage: 0.2

## Calculation Formula
1. Normalize each metric to 0-10 scale
2. Apply weight to each metric
3. Sum all weighted metrics to obtain KPI (0-10)
4. Store KPI in processed dataset