# PreseHome - KPIs

A lightweight Engineering Metrics Platform that extracts code quality data from SonarCloud, transforms it into actionable KPIs, and feeds both engineering dashboards in Grafana and executive reporting in Microsoft Power BI.

The project demonstrates how engineering metrics pipelines can support technical governance and data-driven decision making in software organizations.

## Engineering Metrics Pipeline

This project implements a lightweight engineering metrics pipeline designed to monitor the technical health of a software product and provide actionable insights for both engineering teams and management.

The pipeline follows a typical data engineering flow:

1. Metric extraction

    The system collects code quality metrics from SonarCloud through its API.

2. KPI calculation

    Raw metrics are processed using Python scripts to generate higher-level indicators such as:
- Code Quality Score
- Technical Debt Ratio
- Application Health Index

3. Dataset generation

    The processed metrics are exported into structured datasets that can be consumed by visualization and reporting tools.

4. Dashboard integration

    The datasets feed two different visualization layers:
- Technical observability dashboards in Grafana
- Executive reporting dashboards in Microsoft Power BI

    This architecture simulates how many organizations implement engineering metrics platforms to monitor software quality and support data-driven decision making.



Automation of the pipeline is implemented using CI/CD workflows with scheduled data processing scripts.

## Technical vs Executive Dashboards

The project intentionally separates technical monitoring from executive reporting, as these audiences require different levels of information.

### Grafana — Technical Engineering Observability

Dashboards in Grafana focus on low-level engineering metrics used by developers and DevOps teams.

- Typical metrics include:
- Code coverage
- Bugs detected
- Vulnerabilities
- Code smells
- Technical debt
- Historical trends of code quality metrics

These dashboards allow engineers to monitor the technical state of the codebase and quickly identify quality issues.

### Power BI — Executive KPI Reporting

Dashboards in Microsoft Power BI provide aggregated indicators designed for management, PMO, or product leadership.

Instead of raw metrics, they display higher-level KPIs such as:
- Quality Score
- Application Health Index
- Technical Debt Ratio
- Quality evolution over time
These dashboards help stakeholders understand the overall health of the application and support strategic decisions.

## Architecture

Separating technical metrics from executive KPIs reflects a common practice in engineering organizations:

- Operational dashboards for engineering teams
- Business intelligence dashboards for leadership and governance

This dual-layer reporting model helps ensure that both technical and business stakeholders can access the information relevant to their decision-making process.

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

**Note on the OneDrive box:** the OneDrive upload integration shown above (Microsoft Graph API, OAuth device-code sign-in, retry logic — see `src/utils/onedrive/`) is fully built and working, but is currently a **standalone utility, not called automatically** by the pipeline. Power BI's live data source is instead planned to read directly from this GitHub repo (the `GitHub (JSON)` box already shown), which avoids the extra OneDrive/Azure hop entirely for automation. The OneDrive code is kept available for manual use or future adoption — see `CLAUDE.md`'s "Utilities" section for how to run it.

## Repository Structure

src/
    extraction/      # metric collection
    processing/      # KPI calculations
    export/          # dataset generation
    utils/
        onedrive/    # standalone OneDrive upload utility (not wired into the pipeline)

data/
    raw/             # raw metrics from APIs
    processed/       # processed KPI data

datasets/
    engineering_metrics.json

dashboards/
    grafana/         # technical observability
    powerbi/         # executive reporting

## Enviroment installation for Linux

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

For extract metrics from SonarCloud:

```bash
python src/extraction/extract_sonar.py
```

For calculate KPIs:
```bash
python src/processing/calculate_kpis.py
```

## Definition of Done

A user story is considered completed when:

- The corresponding operational tasks are implemented
- The pipeline executes successfully
- KPI datasets are generated correctly
- Documentation is updated
- The pull request is merged
- All related issues are closed

## Project Goals

This project was developed to explore how engineering metrics
can be extracted, processed, and visualized to support technical
governance and decision-making in software teams.

It also serves as a practical example of applying agile project
management practices and automated data pipelines.
