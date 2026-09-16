# Sprint 4 Review

## Completed:
- Implement scheduled GitHub Actions workflow for the KPI pipeline #41
- Commit pipeline outputs back to the repo from the scheduled workflow #42

## In progress:
- Switch Power BI's data source to read directly from GitHub #43 — depends on #41/#42 being live on `main` (scheduled `cron` triggers only fire from the default branch, and Power BI's Web connector needs a stable `main`-hosted URL to point at). Verification against real Power BI Service is pending.

## Artifacts:
- .github/workflows/main.yml
