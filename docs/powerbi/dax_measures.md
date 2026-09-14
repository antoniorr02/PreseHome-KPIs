# Power BI — DAX Measures Reference

This documents the DAX model behind the executive KPI report (`dashboards/powerbi/Executive Report - PreseHome.pbix`, issue #38). It's written out here as plain text because DAX measures live inside the `.pbix` binary and aren't visible browsing the repo otherwise.

> This reflects the measures as planned and built through Power BI Service's web editor. If you renamed anything while working through the "New measure"/"New table" dialogs, update this doc to match what's actually saved in the report — it should always describe the real `.pbix`, not the other way around.

## Data model

**Single table, `kpi_history`** — imported from `datasets/kpi_history.json` (flattened to CSV via `src/utils/powerbi/export_history_csv.py`; see README's "Keeping the Power BI Report Up to Date"). Relevant columns: `timestamp`, `kpi_score`, `norm_bugs`, `norm_vulnerabilities`, `norm_code_smells`, `norm_coverage`.

**One disconnected table, `Metric`** — a small hand-built table with no relationship to `kpi_history`, used purely as a category axis for the breakdown chart:

```dax
Metric = 
DATATABLE(
    "MetricName", STRING,
    {
        { "Bugs" }, { "Vulnerabilities" }, { "Code Smells" }, { "Coverage" }
    }
)
```

This is the standard "disconnected parameter table" pattern: instead of unpivoting `norm_bugs`/`norm_vulnerabilities`/`norm_code_smells`/`norm_coverage` into rows at the Power Query layer, the four values stay as separate columns and a measure picks the right one per category at query time (see `Latest Norm Score` below). Keeps the table narrow and pushes the "which column" decision into DAX instead of ETL.

## Base measures

One `MAX`-based measure per numeric field. Using `MAX` (rather than relying on a column's implicit aggregation) means every visual explicitly states its own aggregation, and these measures are reused by the "latest value" measures below instead of repeating the `MAX(kpi_history[...])` expression everywhere.

```dax
KPI Score            = MAX ( kpi_history[kpi_score] )
Norm Bugs             = MAX ( kpi_history[norm_bugs] )
Norm Vulnerabilities  = MAX ( kpi_history[norm_vulnerabilities] )
Norm Code Smells      = MAX ( kpi_history[norm_code_smells] )
Norm Coverage         = MAX ( kpi_history[norm_coverage] )
```

`KPI Score` is also used directly (no wrapper needed) on the trend line chart — plotted against `timestamp`, `MAX` per point correctly returns that run's single value.

## "Latest value" pattern

`kpi_history` has no built-in "current row" concept — it's an append-only log, one row per pipeline run. The gauge/card visual needs "whatever the most recent run's score was," which this pattern derives without needing a separate single-row data source:

```dax
Latest KPI Score = 
VAR LatestTimestamp = MAX ( kpi_history[timestamp] )
RETURN
    CALCULATE ( [KPI Score], kpi_history[timestamp] = LatestTimestamp )
```

`MAX(kpi_history[timestamp])` finds the most recent run's timestamp under whatever filter context is active, then `CALCULATE` re-filters the table down to just that one row before re-evaluating `[KPI Score]`. This avoids `LASTDATE()` deliberately — `LASTDATE` is built for a marked date table tied to a continuous calendar, whereas `timestamp` here is a plain irregular datetime column (whatever moments the pipeline happened to run), so a direct `MAX` + equality filter is the more correct tool.

Bound to the report's Gauge visual, min `0`, max `10`.

## Dynamic breakdown measure

This is where the `Metric` disconnected table earns its keep — one measure serves all four bars in the breakdown chart, switching on which category the visual is currently rendering:

```dax
Latest Norm Score = 
VAR LatestTimestamp = MAX ( kpi_history[timestamp] )
VAR SelectedMetric  = SELECTEDVALUE ( Metric[MetricName] )
RETURN
    SWITCH (
        SelectedMetric,
        "Bugs",            CALCULATE ( [Norm Bugs], kpi_history[timestamp] = LatestTimestamp ),
        "Vulnerabilities",  CALCULATE ( [Norm Vulnerabilities], kpi_history[timestamp] = LatestTimestamp ),
        "Code Smells",      CALCULATE ( [Norm Code Smells], kpi_history[timestamp] = LatestTimestamp ),
        "Coverage",         CALCULATE ( [Norm Coverage], kpi_history[timestamp] = LatestTimestamp )
    )
```

Bound to a bar chart: Axis = `Metric[MetricName]`, Value = `[Latest Norm Score]`. Each bar's category filters `Metric` down to one row, `SELECTEDVALUE` reads which one, and `SWITCH` routes to the matching base measure — re-applying the same "latest timestamp" filter each branch needs.

## Report layout

| Visual | Type | Bound to |
|---|---|---|
| KPI Score | Gauge/Card | `[Latest KPI Score]` |
| Component breakdown | Bar chart | `Metric[MetricName]` / `[Latest Norm Score]` |
| Score trend | Line chart | `kpi_history[timestamp]` / `[KPI Score]` |

All built via Power BI Service's browser-based report editor (Modeling → New measure / New table), not Power BI Desktop — this project is developed on Linux, and Power BI Desktop is Windows-only. See README's "Keeping the Power BI Report Up to Date" for why that means this report has no live refresh yet.
