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