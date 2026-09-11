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