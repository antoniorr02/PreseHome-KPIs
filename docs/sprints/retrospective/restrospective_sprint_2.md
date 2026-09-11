# Sprint 2 Retrospective

## What went well
- KPI calculation engine implemented and validated
- Configurable weights via config.json proved flexible and clean
- Clear separation between normalization and calculation layers

## What could be improved
- Architecture decisions were not fully evaluated upfront.
  Jenkins was initially considered as a CI/CD option but its
  complexity and infrastructure requirements make it unnecessary
  for a single-project pipeline. This should have been discarded
  during the initial architecture design phase in favour of
  GitHub Actions, which is simpler, free, and natively integrated
  with the repository.

- The storage and reporting strategy for Power BI was not defined
  early enough. The need for a cloud storage layer (OneDrive) to
  enable automatic dashboard refresh in Power BI Service should
  have been identified during architecture design, not discovered
  during sprint planning for Sprint 4.

## Action items
- Define and close all architecture decisions before Sprint 3
  to avoid mid-pipeline redesigns
- Document ADR (Architecture Decision Record) for CI/CD tool
  selection and cloud storage choice as reference for future
  similar projects