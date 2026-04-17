import { Link } from "react-router-dom";

const bugArchitectureHighlights = [
    {
        title: "System 1",
        description: "Parses the Jira title, extracts division, table, and issue details, and classifies whether the incident is infra-related or data-related.",
    },
    {
        title: "System 2",
        description: "Resolves ownership, source tables, target tables, and old-to-new column mapping from the workbook fixtures.",
    },
    {
        title: "System 3",
        description: "Analyzes the old and new scripts independently, compares the behaviors, and produces a focused human-readable investigation summary.",
    },
    {
        title: "System 4",
        description: "Queries SQLite target-table fixtures, runs deterministic SQL diagnostics, and grounds the final explanation against the new-script analysis.",
    },
    {
        title: "Orchestrator",
        description: "Runs the end-to-end flow for the UI and returns the structured response that powers the investigation dashboard.",
    },
];

const bugFlowSteps = [
    "The user submits a Jira title from the UI.",
    "The orchestrator calls System 1 to parse the title, extract the issue, and classify the routing path.",
    "If the issue is data-related, System 2 resolves target-table metadata and old-to-new column mappings.",
    "System 3 analyzes the old script and new script independently using the resolved mapping context.",
    "System 4 queries SQLite target-table fixtures, runs deterministic diagnostics, and compares those findings with the new-script analysis.",
    "The orchestrator returns a structured response with root cause, SQL evidence, and next-step guidance for the analyst.",
];

const system4Highlights = [
    {
        title: "SQLite Evidence Layer",
        details: "System 4 uses seeded current-target-table and support-table fixtures so every SQL finding is grounded in reproducible mock data.",
    },
    {
        title: "Deterministic Checks",
        details: "It runs issue-focused SQL diagnostics such as missing-column checks, duplicate detection, and basic data-shape validation before any optional LLM explanation.",
    },
    {
        title: "Script Comparison",
        details: "The SQL symptoms are compared with the new-script analysis so the output connects target-table behavior back to transformation logic.",
    },
    {
        title: "Analyst Output",
        details: "The UI surfaces current target-table query results, diagnostic SQL findings, and a grounded SQL-versus-script explanation with code references.",
    },
];

const bugDataSources = [
    {
        title: "Column Mapping Workbook",
        details: "Gavin2-to-Gavin3 renamed-column mappings for each target table, including old and new data types.",
    },
    {
        title: "Table Metadata Workbook",
        details: "Division ownership, source tables, old and new target tables, support team, owners, and script paths.",
    },
    {
        title: "Old and New PySpark Scripts",
        details: "Repo-local script fixtures used to compare legacy logic against the new Gavin3 transformation flow.",
    },
    {
        title: "SQLite Target Table Fixtures",
        details: "Seeded target-table and support-table rows used directly by System 4 for issue-focused SQL diagnostics and grounded comparison.",
    },
    {
        title: "Scenario Catalog",
        details: "Curated bug scenarios that keep the mock data aligned to realistic migration regressions.",
    },
];

const sampleMappingRows = [
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "entity_id",
        new_column_name: "EntityIdentifier",
        data_type_old: "string",
        data_type_new: "string",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "entity_name",
        new_column_name: "EntityDisplayName",
        data_type_old: "string",
        data_type_new: "string",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "date_updated",
        new_column_name: "UPDATEDDATE",
        data_type_old: "timestamp",
        data_type_new: "timestamp",
    },
    {
        old_system: "Gavin2",
        new_system: "Gavin3",
        old_table_name: "tentity_old",
        new_table_name: "tentity_new",
        old_column_name: "updated_by",
        new_column_name: "UpdatedByUser",
        data_type_old: "string",
        data_type_new: "string",
    },
];

const sampleOldScript = `from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "entity_id",
        "date_updated",
        "updated_by",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="entity_id", how="left")
        .select(
            F.col("base.entity_id").alias("entity_id"),
            F.col("base.entity_name").alias("entity_name"),
            F.col("audit.date_updated").alias("date_updated"),
            F.col("audit.updated_by").alias("updated_by"),
        )
    )`;

const sampleNewScript = `from pyspark.sql import functions as F


def transform(src_tentity_base, src_tentity_audit):
    audit_snapshot = src_tentity_audit.select(
        "EntityIdentifier",
        "UpdatedByUser",
    )

    return (
        src_tentity_base.alias("base")
        .join(audit_snapshot.alias("audit"), on="EntityIdentifier", how="left")
        .select(
            F.col("base.EntityIdentifier").alias("EntityIdentifier"),
            F.col("base.EntityDisplayName").alias("EntityDisplayName"),
            F.col("audit.UpdatedByUser").alias("UpdatedByUser"),
        )
    )`;

const analystOutputs = [
    "Issue summary and routing decision from the orchestrator.",
    "Old target table and new target table context from System 2.",
    "Issue-focused column mapping plus full target-table mapping coverage.",
    "Old script analysis and new script analysis from System 3.",
    "Current target-table SQL query results and deterministic diagnostic SQL checks from System 4.",
    "A grounded SQL-versus-new-script explanation with affected code references.",
    "Likely root cause, possible resolutions, and recommended next step.",
    "Evidence snippets and script references when expanded.",
];

const bugAiUsageCards = [
    {
        title: "Where AI Is Used",
        details: "System 1 is rules-first and only uses AI as a fallback for low-confidence parsing or classification. System 2 stays fully deterministic, and System 3 remains the main AI analysis layer.",
    },
    {
        title: "How AI Is Used",
        details: "For a normal data issue, System 3 runs old-script analysis, new-script analysis, and synthesis. System 4 can add one extra grounded comparison call after deterministic SQL diagnostics to explain the target-table symptoms against the new script.",
    },
    {
        title: "Current Model",
        details: "The shared OpenAI client is currently configured to use gpt-4o-mini by default unless OPENAI_CHAT_MODEL is overridden in the environment.",
    },
    {
        title: "Why This Model",
        details: "It keeps the POC fast and inexpensive while still being strong enough for structured JSON analysis and grounded comparison of script and SQL evidence.",
    },
];

const bugAiCostNotes = [
    "System 1 normally stays rule-based, but a low-confidence title can trigger one extra fallback LLM call for parsing and classification.",
    "A typical data investigation triggers three LLM calls in System 3: old-script analysis, new-script analysis, and synthesis.",
    "System 4 can add one more grounded LLM call after deterministic SQL diagnostics to explain how current target-table data lines up with the new script.",
    "Using the current default model gpt-4o-mini, a small POC investigation usually lands in the low-thousand-token range and is typically a fraction of a cent to a few tenths of a cent per issue.",
    "A reasonable working estimate for this POC is about $0.003 to $0.007 per normal data issue, with slightly higher cost when System 1 also needs the AI fallback.",
    "Infra issues short-circuit after System 1, so they do not need the full LLM path in Systems 3 and 4.",
    "Costs can increase if we send larger script excerpts, longer evidence blocks, or switch to a more capable model.",
];

const monitoringOverviewCards = [
    {
        title: "Primary Use Case",
        details: "Monitor scheduled Azure Data Factory or Azure Synapse pipelines in one operational view instead of waiting for issue-by-issue investigation.",
    },
    {
        title: "Operational Focus",
        details: "The dashboard prioritizes historical health, recent failures, retries, and duration regressions rather than second-by-second live status.",
    },
    {
        title: "Current Data Mode",
        details: "The POC currently runs on seeded observability fixtures that resemble Log Analytics output so the UI and API remain deterministic during development.",
    },
    {
        title: "Where To Use It",
        details: "The interactive experience lives on the live monitoring dashboard at /#/observability, while this section explains the architecture and behavior behind it.",
    },
];

const monitoringArchitectureSteps = [
    "Azure Data Factory or Azure Synapse emits diagnostic events for pipeline, activity, and trigger runs.",
    "Those diagnostics flow into a Log Analytics workspace that becomes the primary historical telemetry source.",
    "The FastAPI backend queries and normalizes the run data, then joins it with app-owned metadata such as cadence, owner, and criticality.",
    "The observability API returns summary metrics, grouped pipeline health, drilldown detail, AI summary context, and natural-language query results.",
    "The React dashboard renders filters, attention items, grouped health views, run history, and AI-assisted monitoring panels.",
];

const monitoringCapabilities = [
    {
        title: "Dashboard Filters",
        details: "Time window, cadence, status, owner, criticality, and pipeline search help narrow the operational scope quickly.",
    },
    {
        title: "Attention Inbox",
        details: "The dashboard surfaces the pipelines that need eyes first, including failures, retries, and regression signals.",
    },
    {
        title: "Grouped Health Views",
        details: "Pipelines are grouped by cadence so operators can compare daily, weekly, and monthly health from the same screen.",
    },
    {
        title: "Pipeline Drilldown",
        details: "Each pipeline has run history, retry summary, activity-level trends, failure details, and recent execution context.",
    },
    {
        title: "AI Assistance",
        details: "Operators can generate an AI summary of the current dashboard state or ask a natural-language question grounded in backend-provided data.",
    },
];

const monitoringApiSurface = [
    {
        endpoint: "GET /observability/summary",
        details: "Returns summary metrics and the attention inbox used for the top-level monitoring view.",
    },
    {
        endpoint: "GET /observability/pipelines",
        details: "Returns grouped pipeline health and list data filtered by cadence, status, owner, criticality, and search.",
    },
    {
        endpoint: "GET /observability/pipelines/{pipeline_name}",
        details: "Returns run history, retry patterns, activity summaries, and detailed failure context for a selected pipeline.",
    },
    {
        endpoint: "POST /observability/summary-ai",
        details: "Builds a grounded AI summary from the current summary metrics and grouped pipeline data already loaded by the UI.",
    },
    {
        endpoint: "POST /observability/query",
        details: "Translates a natural-language question into a safe observability query plan and summarized response grounded in backend results.",
    },
];

const monitoringDataSources = [
    {
        title: "ADFPipelineRun",
        details: "Primary pipeline-level run history for summary metrics, latest status, duration tracking, and trend analysis.",
    },
    {
        title: "ADFActivityRun",
        details: "Activity-level telemetry used for detailed failure context, retry analysis, and downstream drilldown insights.",
    },
    {
        title: "ADFTriggerRun",
        details: "Trigger execution context used to explain cadence behavior, missed schedules, and trigger-linked run patterns.",
    },
    {
        title: "App-Owned Metadata",
        details: "Cadence, owner, criticality, and related business metadata are maintained by the application instead of being inferred only from logs.",
    },
    {
        title: "Seeded Mock Fixtures",
        details: "The current POC uses fixture bundles under the observability fixture root so the same backend processing path can later point at a real Log Analytics workspace.",
    },
];

const monitoringAiCards = [
    {
        title: "Summary Generation",
        details: "The AI summary endpoint explains the current dashboard state by grounding every statement in the summary metrics and grouped pipeline rows already fetched by the backend.",
    },
    {
        title: "Natural-Language Querying",
        details: "The query assistant converts plain-English operational questions into a safe query plan and response shape instead of letting the browser hit telemetry sources directly.",
    },
    {
        title: "Guardrails",
        details: "All Azure credentials, workspace access, and query execution remain server-side, so AI assistance works only on backend-provided observability data.",
    },
];

function DocsAccordion({ badge, copy, defaultOpen = false, title, children }) {
    return (
        <details className="panel docs-accordion" open={defaultOpen}>
            <summary>
                <div className="docs-accordion-title">
                    <h2>{title}</h2>
                    <span className="metric-badge">{badge}</span>
                </div>
                <p className="docs-accordion-copy">{copy}</p>
            </summary>
            <div className="docs-section-stack">{children}</div>
        </details>
    );
}

export default function DocsPage() {
    return (
        <section className="docs-stack">
            <section className="hero-card">
                <div className="hero-actions">
                    <div>
                        <p className="eyebrow">Project Docs</p>
                        <h1>Bug Management and Monitoring POC documentation</h1>
                        <p className="hero-copy">
                            This page covers both sides of the POC: the four-stage Jira bug investigation flow,
                            including System 4 SQL diagnostics, and the Azure pipeline monitoring experience powered
                            by the live observability dashboard.
                        </p>
                    </div>
                    <Link to="/" className="ghost nav-button">
                        Back To Investigation
                    </Link>
                    <Link to="/observability" className="ghost nav-button">
                        Open Live Monitoring
                    </Link>
                </div>
            </section>

            <section className="docs-accordion-stack">
                <DocsAccordion
                    defaultOpen
                    title="Bug Management"
                    badge="Four-stage investigation"
                    copy="Jira title parsing, script analysis, and System 4 SQL diagnostics for grounded migration investigations."
                >
                    <article className="docs-panel">
                        <p className="section-kicker">Architecture</p>
                        <h3>Service Responsibilities</h3>
                        <figure className="docs-figure">
                            <img src="/docs-images/architecture-diagram.png" alt="Architecture diagram for the bug investigation platform" />
                            <figcaption>
                                High-level architecture showing the React UI, orchestrator, four investigation stages,
                                workbook inputs, SQLite fixtures, script fixtures, and the grounded analysis flow.
                            </figcaption>
                        </figure>
                        <div className="docs-card-grid">
                            {bugArchitectureHighlights.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.description}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data Flow</p>
                        <h3>How a request moves through the system</h3>
                        <figure className="docs-figure">
                            <img src="/docs-images/data-flow-diagram.png" alt="Data flow diagram for Jira title investigation" />
                            <figcaption>
                                End-to-end flow from Jira title input through parsing, metadata resolution, old and
                                new script analysis, System 4 SQL diagnostics, and final structured output.
                            </figcaption>
                        </figure>
                        <ol className="docs-flow-list">
                            {bugFlowSteps.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ol>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">System 4</p>
                        <h3>SQL diagnostics and grounded comparison</h3>
                        <div className="docs-card-grid">
                            {system4Highlights.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data Sources</p>
                        <h3>Mock data used by the POC</h3>
                        <div className="docs-card-grid">
                            {bugDataSources.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Sample Data</p>
                        <h3>Example workbook rows and script inputs</h3>
                        <p className="hero-copy docs-copy">
                            This sample is taken from the <code>tentity_old</code> to <code>tentity_new</code>
                            migration path. It shows the renamed-column mapping and old/new PySpark logic that
                            Systems 2 and 3 resolve before System 4 checks the resulting target-table behavior.
                        </p>

                        <section className="subsection">
                            <h4>Sample Column Mapping Sheet Rows</h4>
                            <div className="table-wrap docs-table-wrap">
                                <table className="mapping-table">
                                    <thead>
                                        <tr>
                                            <th>Old System</th>
                                            <th>New System</th>
                                            <th>Old Table</th>
                                            <th>New Table</th>
                                            <th>Old Column</th>
                                            <th>New Column</th>
                                            <th>Old Type</th>
                                            <th>New Type</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sampleMappingRows.map((row) => (
                                            <tr key={`${row.old_column_name}-${row.new_column_name}`}>
                                                <td>{row.old_system}</td>
                                                <td>{row.new_system}</td>
                                                <td>{row.old_table_name}</td>
                                                <td>{row.new_table_name}</td>
                                                <td>{row.old_column_name}</td>
                                                <td>{row.new_column_name}</td>
                                                <td>{row.data_type_old}</td>
                                                <td>{row.data_type_new}</td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </section>

                        <section className="docs-script-grid">
                            <div className="docs-script-card">
                                <div className="docs-script-header">
                                    <div>
                                        <p className="section-kicker">Legacy Script</p>
                                        <h4>Old PySpark Example</h4>
                                    </div>
                                    <span className="metric-badge">tentity_old flow</span>
                                </div>
                                <pre className="code-block">{sampleOldScript}</pre>
                            </div>

                            <div className="docs-script-card">
                                <div className="docs-script-header">
                                    <div>
                                        <p className="section-kicker">Target Script</p>
                                        <h4>New PySpark Example</h4>
                                    </div>
                                    <span className="metric-badge">tentity_new flow</span>
                                </div>
                                <pre className="code-block">{sampleNewScript}</pre>
                            </div>
                        </section>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Output</p>
                        <h3>What the analyst sees in the UI</h3>
                        <ul className="detail-list">
                            {analystOutputs.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ul>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">AI Layer</p>
                        <h3>How AI is used in this POC</h3>
                        <div className="docs-card-grid">
                            {bugAiUsageCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                        <div className="docs-card-grid">
                            <div className="docs-info-card">
                                <h4>Estimated Cost</h4>
                                <ul className="detail-list">
                                    {bugAiCostNotes.map((item) => (
                                        <li key={item}>{item}</li>
                                    ))}
                                </ul>
                            </div>
                            <div className="docs-info-card">
                                <h4>Pricing Reference</h4>
                                <p>
                                    Current pricing should be checked against the official OpenAI pricing page before
                                    using the estimate operationally.
                                </p>
                                <p>
                                    OpenAI pricing:{" "}
                                    <a
                                        className="docs-link"
                                        href="https://platform.openai.com/docs/pricing"
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        platform.openai.com/docs/pricing
                                    </a>
                                </p>
                                <p>
                                    The default model value comes from the shared client in the repo and is currently set to
                                    <code> gpt-4o-mini </code>.
                                </p>
                            </div>
                        </div>
                    </article>
                </DocsAccordion>

                <DocsAccordion
                    title="Monitoring"
                    badge="Live dashboard docs"
                    copy="Azure pipeline health, grouped monitoring, backend-served observability APIs, and AI-assisted operational analysis."
                >
                    <article className="docs-panel">
                        <p className="section-kicker">Overview</p>
                        <h3>Monitoring POC overview</h3>
                        <p className="hero-copy docs-copy">
                            The monitoring side of the POC acts as an operational dashboard for Azure Data Factory and
                            Azure Synapse pipeline health. It complements the issue-driven investigation flow by
                            helping operators identify failing, retrying, or slowing pipelines before they escalate into
                            individual bug investigations.
                        </p>
                        <div className="docs-card-grid">
                            {monitoringOverviewCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                            <div className="docs-info-card">
                                <h4>Live Route</h4>
                                <p>
                                    Use the{" "}
                                    <Link className="docs-link" to="/observability">
                                        live monitoring dashboard
                                    </Link>{" "}
                                    for the interactive experience described in this section.
                                </p>
                            </div>
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Architecture</p>
                        <h3>Monitoring architecture and data path</h3>
                        <ol className="docs-flow-list">
                            {monitoringArchitectureSteps.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ol>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Capabilities</p>
                        <h3>Dashboard capabilities</h3>
                        <div className="docs-card-grid">
                            {monitoringCapabilities.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">API Surface</p>
                        <h3>Backend API surface</h3>
                        <div className="docs-card-grid">
                            {monitoringApiSurface.map((item) => (
                                <div key={item.endpoint} className="docs-info-card">
                                    <h4>
                                        <code>{item.endpoint}</code>
                                    </h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">Data</p>
                        <h3>Data sources and seed strategy</h3>
                        <div className="docs-card-grid">
                            {monitoringDataSources.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="docs-panel">
                        <p className="section-kicker">AI Layer</p>
                        <h3>AI assistance in monitoring</h3>
                        <div className="docs-card-grid">
                            {monitoringAiCards.map((item) => (
                                <div key={item.title} className="docs-info-card">
                                    <h4>{item.title}</h4>
                                    <p>{item.details}</p>
                                </div>
                            ))}
                        </div>
                    </article>
                </DocsAccordion>
            </section>
        </section>
    );
}
