    +------------------+
    | GitHub Actions   |
    | (daily cron +    |
    |  on-demand)      |
    +--------+---------+
             |
             | triggers
             v
                 +------------------+
                 |    SonarCloud    |
                 +---------+--------+
                           |
                           v
                +--------------------+
                |  Extraction Layer  |
                |   (Python scripts) |
                +---------+----------+
                          |
                          v
                +--------------------+
                |  KPI Engine        |
                |  (Processing)      |
                +---------+----------+
                          |
                          v
                +--------------------+
                |  Dataset Layer     |
                +---------+----------+
                          |
               +----------+----------+
               |                     |
               v                     v
         +-----------+         +-----------+
         | InfluxDB  |         |  GitHub   |
         |  (Cloud)  |         |  (JSON)   |
         +-----+-----+         +-----+-----+
               |                     |
               v               +-----+-----+
          +---------+          |           |
          | Grafana |          v           v
          | (Tech   |    +----------+ +-----------+
          |Dashboard)|   |  Backup  | |  Power BI |
          +---------+    | /Migrate | | (Executive|
                          +----------+ | Dashboard)|
                                       +-----------+

GitHub Actions also performs the final commit into the `GitHub (JSON)`
box (issues #41/#42) — the same workflow both triggers the pipeline
and pushes its output back to the repo.

**Box notes:**
- **GitHub Actions** — `.github/workflows/main.yml` runs the pipeline daily (cron) plus on-demand (`workflow_dispatch`), and commits `data/raw/`, `data/processed/`, and `datasets/kpi_history.json` back to `main` (issues #41, #42).
- **GitHub (JSON)** — the live handoff point. `datasets/kpi_history.json` gets committed here on every scheduled run, and serves two purposes from there: historical backup, and Power BI's live data source.
- **Power BI** — reads `datasets/kpi_history.json` live from the `GitHub (JSON)` box via Power BI Service's Web connector (GitHub REST API + PAT auth) and refreshes on its own schedule (issue #43). See README's "Keeping the Power BI Report Up to Date" for the exact URL/headers, and `docs/powerbi/dax_measures.md` for the DAX model. `dashboards/powerbi/Executive Report - PreseHome.pbix` was built in Power BI Service's browser editor (Linux has no Power BI Desktop).
- **Grafana** — reads directly from InfluxDB (`dashboards/grafana/code_quality_dashboard.json`, importable as-is).
- Screenshots of both dashboards: `docs/screenshots/`.

**Not in this diagram — OneDrive:** `src/utils/onedrive/` (issue #28) is a fully built, working upload integration, but it's a standalone utility, not called by the pipeline and not part of the live data flow above — Power BI reads from GitHub directly instead (issue #43). Kept available for manual use — see `CLAUDE.md`'s "Utilities" section for how to run it.
