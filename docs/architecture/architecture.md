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
          +---------------+---------------+
          |               |               |
          v               v               v
    +-----------+   +-----------+   +-----------+
    | InfluxDB  |   |  OneDrive |   |  GitHub   |
    |  (Cloud)  |   |  (Excel)  |   |  (JSON)   |
    +-----+-----+   +-----+-----+   +-----+-----+
          |               |               |
          v               v               v
      +--------+    +-----------+    +----------+
      | Grafana|    |  Power BI |    |  Backup  |
      |(Tech   |    | (Executive|    | /Migrate |
      |Dashboard)   | Dashboard)|    +----------+
      +--------+    +-----------+
          
          ^
          |
    +------------------+
    | GitHub Actions   |
    | (cron diario)    |
    | automatiza todo  |
    +------------------+

**Note on the OneDrive box:** this integration (Microsoft Graph API, OAuth device-code sign-in, retry logic — see `src/utils/onedrive/`) is fully built and working, but is currently a standalone utility, not called automatically by the pipeline. Power BI's live data source is instead planned to read directly from the GitHub repo (the `GitHub (JSON)` box), tracked as part of US06. See `CLAUDE.md`'s "Utilities" section for how to run the OneDrive utility manually.

**Note on the Grafana and Power BI boxes:** both dashboards are implemented (issues #37, #38). Grafana reads directly from InfluxDB (`dashboards/grafana/code_quality_dashboard.json`, importable as-is). Power BI's report (`dashboards/powerbi/Executive Report - PreseHome.pbix`) was built in Power BI Service's browser editor rather than Desktop (Linux has no Power BI Desktop) from a one-time flattened-CSV upload, so — unlike the live diagram above implies — it currently has no automatic refresh; see README's "Keeping the Power BI Report Up to Date" and `docs/powerbi/dax_measures.md` for the DAX model behind it. Screenshots of both: `docs/screenshots/`.