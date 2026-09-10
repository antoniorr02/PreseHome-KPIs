# Product Backlog — Engineering Metrics Platform

This backlog defines the main user stories for the Engineering Metrics Platform.  
The objective of the project is to extract software quality metrics from SonarCloud, transform them into KPIs, and provide dashboards for both engineering teams and management.

| ID   | User Story | Acceptance Criteria | Priority | Sprint | Status |
|-----|-------------|--------------------|-----------|--------|--------|
| US01 | As a PMO, I want to create the base repository structure. So that the KPI monitoring system can be developed. | Created scripts. dashbpoards, data and docs folders | High | Sprint 1 | Done |
| US02 | As a PMO, I want to extract code quality metrics from SonarCloud for each repository so that I can evaluate the technical quality of the application and generate a structured dataset from the extracted metrics so that it can be consumed by reporting tools | Metrics **bugs**, **vulnerabilities**, **code smells**, and **coverage** metrics through the SonarCloud API exported to a structured JSON dataset stored in `data/raw` | High | Sprint 1 | Done |
| US03 | As a PMO, I want to calculate engineering KPIs so that I can evaluate the overall technical health of an application | Calculate a weighted KPI score. So that application quality can be evaluated with a single metric.| High | Sprint 2 | In progress |
| US04 | As a PMO, I want to store historical KPI data so that I can analyze trends over time | Historical metrics stored with timestamps in JSON and InfluxDB | High | Sprint 2 | In progress |
| US05 | As a PMO, I want to visualize KPIs in dashboards so that developers and stakeholders can monitor code quality and application health | Technical dashboard implemented in Grafana for engineering metrics; Executive dashboard implemented in Power BI for high-level KPIs, trends, and rankings | Medium | Sprint 3 | Planned |
| US06 | As a PMO, I want to automate the engineering metrics pipeline so that metrics are updated regularly without manual intervention | GitHub Actions workflow that automatically extracts metrics and updates datasets | High | Sprint 4 | Planned |
| US07 | As a PMO, I want to document the architecture of the engineering metrics platform so that the system can be easily understood and maintained | Documentation describing architecture, KPIs, pipelines, and dashboards | Low | - | Planned |

## Prioritization

User stories are prioritized based on their impact on the engineering metrics pipeline and the overall platform architecture.

Priority levels:

- **High** – Core functionality required for the pipeline to operate
- **Medium** – Enhancements improving observability and reporting
- **Low** – Documentation and supporting features