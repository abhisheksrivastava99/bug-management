# Azure Observability Context

## Feature Goal

Add a new UI page for pipeline monitoring and observability.

This page is separate from the existing Jira investigation flow. The current investigation page is issue-driven, while the Azure observability page should act like a dashboard for scheduled pipeline health and history.

## Current Assumption

The pipelines being discussed are assumed to be Azure Data Factory or Azure Synapse integration pipelines, because the current monitoring pattern mentioned is:

- diagnostic settings
- logs sent to a Log Analytics workspace

If the source later turns out to be Azure DevOps pipelines instead, the integration path will be different.

## Confirmed Product Direction

- Create a new page in the UI for pipeline monitoring.
- Live status is not the priority.
- Use Log Analytics workspace as the primary data source.
- Query Azure from the backend only, not directly from the browser.

## Recommended Azure Architecture

```text
ADF/Synapse pipelines
  -> diagnostic settings
  -> Log Analytics workspace
  -> backend query layer (FastAPI)
  -> internal observability API
  -> React observability page
```

## Why Log Analytics Workspace Is The Primary Source

- It is already receiving diagnostics.
- It is better suited for historical analytics than for second-by-second live monitoring.
- It supports the kind of metrics needed for this feature:
  - last run duration
  - last 7 runs average duration
  - success rate
  - failure count
  - latest failure message
  - 30-day trends
- For a POC, it keeps the architecture simpler and more stable than combining multiple Azure APIs early.

## Azure Data Sources To Use

For Azure Data Factory:

- `ADFPipelineRun`
- `ADFActivityRun`
- `ADFTriggerRun`

For Azure Synapse:

- `SynapseIntegrationPipelineRuns`
- `SynapseIntegrationActivityRuns`
- `SynapseIntegrationTriggerRuns`

The first table in each set is the main source for pipeline-level monitoring.

## Recommended Backend Responsibilities

- Authenticate to Azure using Microsoft Entra ID.
- Query the Log Analytics workspace using KQL.
- Normalize raw LAW rows into clean app models.
- Merge pipeline telemetry with app-owned metadata such as cadence and ownership.
- Expose app endpoints for the UI.

## Recommended UI Responsibilities

- Show overall summary cards.
- Group pipelines by cadence: daily, weekly, monthly.
- Show per-pipeline rows/cards with last run status, duration, and recent averages.
- Allow drilldown into recent run history and failure details.

## Important Design Note About Cadence

Daily, weekly, and monthly grouping should be treated as application metadata, not inferred only from logs.

Recommended approach:

- maintain a small config or metadata mapping for pipeline name or pipeline ID
- store cadence, owner, and criticality there
- join that metadata with LAW query results in the backend

## Suggested Internal API Shape

- `GET /observability/summary`
- `GET /observability/pipelines`
- `GET /observability/pipelines/{pipeline_name}`

## Suggested Core Fields Per Pipeline

- `pipeline_name`
- `cadence`
- `owner`
- `criticality`
- `last_run_status`
- `last_run_start`
- `last_run_end`
- `last_run_duration_seconds`
- `average_duration_last_7_runs`
- `success_rate_30d`
- `failure_count_30d`
- `latest_error_message`

## Query Strategy

For the first version:

- use simple KQL to fetch recent pipeline run rows from LAW
- perform some aggregation in Python for maintainability
- move more aggregation into KQL later only if scale or performance requires it

## Security Guidance

- Keep Azure credentials and LAW access on the server side only.
- Do not query LAW directly from the React app.
- Prefer Microsoft Entra ID over ad hoc browser-side approaches.

## POC Recommendation: Demo Azure Account Vs Mock LAW Data

Recommended path:

- start with seeded or mock LAW data for the first implementation phase
- add a demo Azure account later for integration validation

Reasoning:

- mock data is faster, cheaper, and deterministic
- it lets the team build UI, response models, and metric logic without Azure setup friction
- it makes local development and testing much easier
- a demo Azure account is still valuable later to validate auth, permissions, real table schemas, and KQL behavior against actual logs

## Practical Phase Plan

Phase 1:

- build the observability page and backend contract using seeded or mock LAW data
- finalize metrics, layout, and grouping

Phase 2:

- connect the backend query layer to a demo Azure environment
- validate workspace auth, table names, KQL, and data freshness

Phase 3:

- decide whether the real Azure connection should replace mock mode entirely or coexist behind a config flag

## Current Recommendation Summary

For this POC, do not block progress on setting up a demo Azure account immediately.

Use mock or seeded LAW data first, then connect to a demo Azure environment once the product shape and backend contract are stable.

## Seed Data Strategy

Recommended starting point:

- use seeded mock data that resembles LAW pipeline-run records
- keep the seed data close to the eventual Azure shape
- normalize it through the same backend processing path that the real Azure provider will use later

This reduces rework when the real LAW integration is added.

## Recommended Seed Data Structure

Use two layers of seed data:

1. pipeline metadata
2. pipeline run history

Suggested metadata fields:

- `pipeline_name`
- `pipeline_id`
- `cadence`
- `owner`
- `criticality`
- `business_domain`
- `schedule_timezone`
- `schedule_time`
- optional schedule details such as `day_of_week` or `day_of_month`
- `scenario_profile`

Suggested run-history fields:

- `PipelineName`
- `RunId`
- `Status`
- `Start`
- `End`
- `TimeGenerated`
- `FailureType`
- `ErrorMessage`
- `TriggerType`
- `TriggerName`
- optional Azure identifiers such as factory or resource ID

## Recommended Seed Data Approach

Best option for the POC:

- store static metadata
- generate run-history seed data from scenario profiles

This keeps the data realistic while avoiding stale hard-coded dates.

Example scenario profiles:

- healthy_stable
- duration_regression
- intermittent_failures
- repeated_failures
- missed_schedule
- recovered_after_failure

## Why Scenario-Driven Seed Data Is Better

- it gives predictable edge cases for the UI
- it helps validate backend metric logic
- it keeps dates and recency meaningful
- it is easier to expand than hand-maintaining many raw rows

## Recommended History Depth By Cadence

- daily pipelines: roughly 30 to 45 days of runs
- weekly pipelines: roughly 16 to 20 weeks of runs
- monthly pipelines: roughly 12 to 15 months of runs

This is enough to support last-7-run metrics and basic trend views.

## Core Processing Pipeline

The backend processing flow should be:

1. load raw LAW-like seeded rows
2. validate and normalize timestamps and statuses
3. join pipeline metadata
4. filter to scheduled runs for core operational metrics
5. derive per-pipeline metrics
6. derive cross-pipeline summary metrics
7. shape the final response for the UI

## Important Metric Rules

- treat schedule cadence as metadata, not something inferred only from run history
- default core metrics to scheduled runs
- avoid mixing manual reruns into the main health metrics unless explicitly requested
- keep raw run history available for drilldown

## Cadence-Aware Metric Windows

Fixed windows such as 30 days do not work equally well for daily, weekly, and monthly pipelines.

Recommended approach:

- use `last 7 scheduled runs` for average duration across all cadences
- use cadence-aware health windows for success and failure reporting

Suggested health windows:

- daily: trailing 30 days
- weekly: trailing 12 weeks
- monthly: trailing 12 months

## Recommended Derived Metrics Per Pipeline

- last run status
- last run start and end
- last run duration
- average duration of last 7 scheduled runs
- average duration of previous 7 scheduled runs
- duration trend delta
- success rate over the cadence-aware health window
- failure count over the cadence-aware health window
- latest failure message
- stale or missed-run flag

## Recommended Presentation Shape

Top of page:

- overall summary cards
- pipelines needing attention
- high-level counts by cadence

Middle of page:

- grouped pipeline tables for daily, weekly, and monthly pipelines
- each row shows last run, average duration, trend, success rate, and attention state

Detail view:

- recent run history
- trend of durations
- last failure details
- optional activity-level breakdown later

## Recommended Row-Level Attention Rules

A pipeline should be highlighted when one or more of these are true:

- last run failed
- last run duration is materially above recent average
- success rate has dropped below a threshold
- the pipeline appears stale relative to its expected schedule

## Recommended POC Scope

For the first version, focus on pipeline-level observability only.

Do not start with activity-level drilldown as a core dependency. Add activity-level detail later after the pipeline dashboard shape is validated.
