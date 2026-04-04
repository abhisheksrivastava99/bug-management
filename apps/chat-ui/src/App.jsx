import { useEffect, useMemo, useState } from "react";
import { HashRouter, Link, Navigate, Route, Routes } from "react-router-dom";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

const sampleGroups = [
    {
        label: "Data Issues",
        items: [
            "TTY_TENTITY_Column UPDATEDDATE missing",
            "TTY_TCUSTOMER_Column customer_status_code missing in Gavin3 output",
            "FIN_TINVOICE_Column TotalTax missing",
            "OPS_TSHIPMENT_Column ShipmentStatus missing",
            "TTY_TPROFILE_Column ProfileReviewCompletedTs missing",
            "FIN_TLEDGER_Column LedgerBalanceAmount missing",
            "OPS_TINVENTORY_Column WarehouseOperatingState missing",
            "TTY_TPROFILEAUDIT_Column GovernanceReviewIndex missing",
        ],
    },
    {
        label: "Infra Issues",
        items: [
            "FIN_TORDER_cluster timeout in nightly run",
            "OPS_TSHIPMENT_scheduler timeout in nightly run",
            "TTY_TENTITY_network issue during pipeline run",
            "FIN_TLEDGER_filesystem permission issue in job",
        ],
    },
];

const architectureHighlights = [
    {
        title: "System 1",
        description: "Parses the Jira title, extracts division/table/issue details, and classifies whether the incident is infra-related or data-related.",
    },
    {
        title: "System 2",
        description: "Resolves ownership, target tables, source tables, and old-to-new column mapping from the workbook fixtures.",
    },
    {
        title: "System 3",
        description: "Analyzes the old and new scripts separately, compares the behaviors, and produces a focused human-readable investigation summary.",
    },
    {
        title: "Orchestrator",
        description: "Runs the end-to-end flow for the UI and returns the structured result that powers the dashboard.",
    },
];

const dataSources = [
    {
        title: "Column Mapping Workbook",
        details: "Gavin2 to Gavin3 renamed-column mappings for each target table, including old and new data types.",
    },
    {
        title: "Table Metadata Workbook",
        details: "Division ownership, source tables, old/new target tables, support team, owners, and script paths.",
    },
    {
        title: "Old and New PySpark Scripts",
        details: "Repo-local script fixtures used to compare the legacy logic against the new Gavin3 transformation logic.",
    },
    {
        title: "Scenario Catalog",
        details: "Curated bug scenarios used to make the mock data realistic and aligned to migration regressions.",
    },
];

const analystOutputs = [
    "Issue summary and routing decision",
    "Old target table and new target table",
    "Issue-focused column mapping plus full target-table mapping",
    "Old script analysis and new script analysis",
    "Likely root cause, possible resolutions, and recommended next step",
    "Evidence snippets and script references when expanded",
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

const aiUsageCards = [
    {
        title: "Where AI Is Used",
        details: "System 1 is rules-first and only uses AI as a fallback for low-confidence parsing or classification. System 2 stays fully deterministic, and System 3 is the main AI analysis layer.",
    },
    {
        title: "How AI Is Used",
        details: "For a data issue, the POC can use AI once in System 1 when the title is ambiguous, then System 3 runs old-script analysis, new-script analysis, and final synthesis into a human-readable investigation summary.",
    },
    {
        title: "Current Model",
        details: "The shared OpenAI client is currently configured to use gpt-4o-mini by default unless OPENAI_CHAT_MODEL is overridden in the environment.",
    },
    {
        title: "Why This Model",
        details: "It keeps the POC fast and inexpensive while still being strong enough for structured JSON analysis and grounded comparison of script evidence.",
    },
];

const aiCostNotes = [
    "System 1 normally stays rule-based, but a low-confidence title can trigger one extra fallback LLM call for parsing and classification.",
    "A typical data investigation triggers three LLM calls in System 3: old-script analysis, new-script analysis, and synthesis.",
    "Using the current default model gpt-4o-mini, a small POC investigation usually lands in the low-thousand-token range and is typically a fraction of a cent to a few tenths of a cent per issue.",
    "A reasonable working estimate for this POC is about $0.002 to $0.005 per normal data issue, with slightly higher cost when System 1 also needs the AI fallback.",
    "Infra issues short-circuit after System 1, so they do not need the LLM path in System 3.",
    "Costs can increase if we send larger script excerpts, longer evidence blocks, or switch to a more capable model.",
];

function buildWakeMessage(status, elapsedSeconds) {
    if (status === "warming") {
        const estimatedRemaining = Math.max(0, 60 - elapsedSeconds);
        return `Waking backend... ${elapsedSeconds}s elapsed. Estimated remaining: up to ${estimatedRemaining}s.`;
    }
    if (status === "ready") {
        return `Backend is ready. Last wake/check completed in ${elapsedSeconds}s.`;
    }
    if (status === "failed") {
        return "Unable to reach the backend. Check the Render backend service or try again.";
    }
    return "Useful for Render free-tier demos.";
}

function buildViewModel(result) {
    if (!result) {
        return null;
    }

    const system1 = result.system1 || {};
    const system2 = result.system2 || {};
    const system3 = result.system3 || null;
    const isInfra = !system3;
    const fullMappingSource =
        system2.full_column_mapping ||
        system3?.system2?.full_column_mapping ||
        system2.column_mapping ||
        [];
    const fullMappingRows = dedupeMappingRows(fullMappingSource);

    return {
        isInfra,
        issueSummary: system3?.final_summary || result.final_summary || system1.issue || "",
        overview: [
            { label: "Division", value: system1.division || "N/A" },
            { label: "Table", value: system1.table_name || "N/A" },
            { label: "Issue Type", value: formatLabel(system1.issue_classification) },
            { label: "Routing Team", value: formatLabel(result.routing_team || system1.routing_team) },
            { label: "Old Target Table", value: system2.old_target_table_name || "N/A" },
            { label: "New Target Table", value: system2.new_target_table_name || "N/A" },
            { label: "Support Team", value: system2.support_team || "N/A" },
            { label: "Criticality", value: formatLabel(system2.criticality) },
        ],
        ownership: [
            { label: "Owners", values: system2.owner_users || [] },
            { label: "Source Tables", values: system2.source_tables || [] },
            { label: "Mentioned Columns", values: system1.mentioned_columns || [] },
        ],
        findings: system3
            ? [
                { label: "Likely Root Cause", value: system3.likely_root_cause },
                { label: "Issue Impact", value: system3.issue_impact },
                { label: "Root Cause Family", value: formatLabel(system3.root_cause_family) },
                { label: "Decision", value: formatLabel(system3.decision) },
            ]
            : [],
        mappingRows: dedupeMappingRows(system2.column_mapping || []),
        fullMappingRows,
        analyses: system3
            ? [
                { title: "Old Script Analysis", data: system3.old_analysis, observation: system3.old_script_observation },
                { title: "New Script Analysis", data: system3.new_analysis, observation: system3.new_script_observation },
            ]
            : [],
        resolutions: system3?.possible_resolutions || [],
        recommendedNextStep: system3?.recommended_next_step || "Follow the routed team workflow.",
        evidenceGaps: system3?.evidence_gaps || [],
        unresolvedQuestions: system3?.unresolved_questions || [],
        analysisWarnings: system3?.analysis_warnings || [],
        markdownSummary: result.markdown_summary || "",
        raw: result,
    };
}

function dedupeMappingRows(rows) {
    const seen = new Set();
    return (rows || []).filter((row) => {
        const key = `${row.old_column_name}|${row.new_column_name}|${row.old_table_name}|${row.new_table_name}`;
        if (seen.has(key)) {
            return false;
        }
        seen.add(key);
        return true;
    });
}

function formatLabel(value) {
    if (!value) {
        return "N/A";
    }
    return String(value)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatConfidence(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "N/A";
    }
    return `${Math.round(Number(value) * 100)}%`;
}

function renderValueList(values) {
    if (!values || values.length === 0) {
        return <span className="muted-inline">Not available</span>;
    }
    return (
        <div className="pill-row">
            {values.map((value) => (
                <span key={value} className="info-pill">
                    {value}
                </span>
            ))}
        </div>
    );
}

function AnalysisPanel({ title, observation, data, evidenceExpanded }) {
    return (
        <article className="panel analysis-panel">
            <div className="analysis-header">
                <div>
                    <p className="section-kicker">{title}</p>
                    <h3>{data.script_path?.split("/").pop() || title}</h3>
                </div>
                <div className="metric-cluster">
                    <span className="metric-badge">Decision: {formatLabel(data.decision)}</span>
                    <span className="metric-badge">Confidence: {formatConfidence(data.confidence)}</span>
                </div>
            </div>

            <p className="analysis-summary">{observation || data.summary}</p>

            <div className="chip-group">
                {data.relevant_columns?.map((column) => (
                    <span key={column} className="info-pill">
                        {column}
                    </span>
                ))}
            </div>

            <SectionList title="Observations" items={data.observations} emptyLabel="No observations recorded." />
            <SectionList title="Suspected Causes" items={data.suspected_causes} emptyLabel="No suspected causes recorded." />

            {evidenceExpanded ? (
                <section className="subsection evidence-section">
                    <h4>Evidence and Script References</h4>
                    {data.evidence?.length ? (
                        <div className="evidence-stack">
                            {data.evidence.map((item, index) => (
                                <article key={`${item.file_path}-${item.start_line}-${index}`} className="evidence-card">
                                    <div className="evidence-meta">
                                        <strong>{item.file_path?.split("/").pop() || "Script evidence"}</strong>
                                        <span>
                                            Lines {item.start_line}-{item.end_line}
                                        </span>
                                    </div>
                                    <p className="evidence-reason">{item.reason}</p>
                                    <pre className="code-block">{item.snippet}</pre>
                                </article>
                            ))}
                        </div>
                    ) : (
                        <p className="empty-text">No raw evidence snippets were returned.</p>
                    )}
                </section>
            ) : null}
        </article>
    );
}

function SectionList({ title, items, emptyLabel, children }) {
    return (
        <section className="subsection">
            <h4>{title}</h4>
            {children || null}
            {items ? (
                items.length ? (
                    <ul className="detail-list">
                        {items.map((item, index) => (
                            <li key={`${title}-${index}`}>{item}</li>
                        ))}
                    </ul>
                ) : (
                    <p className="empty-text">{emptyLabel}</p>
                )
            ) : null}
        </section>
    );
}

function InvestigationPage({
    title,
    setTitle,
    loading,
    error,
    viewModel,
    evidenceExpanded,
    setEvidenceExpanded,
    handleSubmit,
    wakeState,
    handleWakeBackend,
}) {
    return (
        <>
            <section className="hero-card">
                <div className="hero-actions">
                    <div>
                        <p className="eyebrow">Bug Management POC</p>
                        <h1>Investigate Gavin2 to Gavin3 migration bugs from a Jira title</h1>
                        <p className="hero-copy">
                            Paste a structured Jira title to see the incident summary, target table metadata, column
                            mapping, old and new script analysis, and recommended next steps in a structured dashboard.
                        </p>
                    </div>
                    <div className="hero-side-actions">
                        <Link to="/docs" className="ghost nav-button">
                            Open Docs
                        </Link>
                        <div className={`wake-card wake-${wakeState.status}`}>
                            <div className="wake-card-header">
                                <p className="section-kicker">Backend Warmup</p>
                                <button
                                    type="button"
                                    className="ghost nav-button wake-button"
                                    onClick={handleWakeBackend}
                                    disabled={wakeState.status === "warming"}
                                >
                                    {wakeState.status === "warming" ? "Waking..." : "Wake Backend"}
                                </button>
                            </div>
                            <p className="wake-copy">{buildWakeMessage(wakeState.status, wakeState.elapsedSeconds)}</p>
                        </div>
                    </div>
                </div>
            </section>

            <section className="panel">
                <form onSubmit={handleSubmit} className="chat-form">
                    <label htmlFor="jira-title">Jira title</label>
                    <textarea
                        id="jira-title"
                        value={title}
                        onChange={(event) => setTitle(event.target.value)}
                        rows={3}
                        placeholder="TTY_TENTITY_Column UPDATEDDATE missing"
                    />
                    <div className="toolbar">
                        <button type="submit" disabled={loading || !title.trim()}>
                            {loading ? "Investigating..." : "Run Investigation"}
                        </button>
                        <div className="sample-group-list">
                            {sampleGroups.map((group) => (
                                <div key={group.label} className="sample-group">
                                    <span className="sample-group-label">{group.label}</span>
                                    <div className="sample-list">
                                        {group.items.map((sample) => (
                                            <button key={sample} type="button" className="ghost" onClick={() => setTitle(sample)}>
                                                {sample}
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                </form>
            </section>

            {error ? <section className="panel error-box">{error}</section> : null}

            {viewModel ? (
                <section className="results-grid">
                    <article className="panel summary-banner">
                        <div>
                            <p className="section-kicker">Issue Summary</p>
                            <h2>{viewModel.issueSummary}</h2>
                            <p className="hero-copy banner-copy">{viewModel.raw.system1?.issue}</p>
                        </div>
                        <div className="next-step-card">
                            <span className="section-kicker">Recommended Next Step</span>
                            <p>{viewModel.recommendedNextStep}</p>
                        </div>
                    </article>

                    <article className="panel">
                        <h2>Service Progress</h2>
                        <div className="steps">
                            {viewModel.raw.steps.map((step) => (
                                <div key={step.name} className={`step-chip step-${step.status}`}>
                                    <strong>{step.name}</strong>
                                    <span>{step.detail}</span>
                                </div>
                            ))}
                        </div>
                    </article>

                    <article className="panel">
                        <h2>Investigation Overview</h2>
                        <div className="stats-grid">
                            {viewModel.overview.map((item) => (
                                <div key={item.label} className="stat-card">
                                    <span className="stat-label">{item.label}</span>
                                    <strong className="stat-value">{item.value || "N/A"}</strong>
                                </div>
                            ))}
                        </div>
                        <div className="ownership-grid">
                            {viewModel.ownership.map((item) => (
                                <div key={item.label} className="ownership-card">
                                    <span className="stat-label">{item.label}</span>
                                    {renderValueList(item.values)}
                                </div>
                            ))}
                        </div>
                    </article>

                    {viewModel.isInfra ? (
                        <article className="panel">
                            <h2>Infra Routing</h2>
                            <p className="analysis-summary">{viewModel.markdownSummary}</p>
                        </article>
                    ) : (
                        <>
                            <article className="panel">
                                <h2>Findings</h2>
                                <div className="findings-grid">
                                    {viewModel.findings.map((item) => (
                                        <div key={item.label} className="finding-card">
                                            <span className="stat-label">{item.label}</span>
                                            <p>{item.value || "N/A"}</p>
                                        </div>
                                    ))}
                                </div>
                            </article>

                            <article className="panel">
                                <div className="section-heading">
                                    <div>
                                        <p className="section-kicker">Target Table Mapping</p>
                                        <h2>Issue-Focused Column Mapping</h2>
                                    </div>
                                    <span className="metric-badge">All rows treated as renamed</span>
                                </div>
                                {viewModel.mappingRows.length ? (
                                    <div className="table-wrap">
                                        <table className="mapping-table">
                                            <thead>
                                                <tr>
                                                    <th>Old Column</th>
                                                    <th>New Column</th>
                                                    <th>Old Type</th>
                                                    <th>New Type</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {viewModel.mappingRows.map((row) => (
                                                    <tr key={`${row.old_column_name}-${row.new_column_name}`}>
                                                        <td>{row.old_column_name}</td>
                                                        <td>{row.new_column_name}</td>
                                                        <td>{row.data_type_old}</td>
                                                        <td>{row.data_type_new}</td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <p className="empty-text">No column mapping rows were returned for this issue.</p>
                                )}

                                <details className="detail-block mapping-details">
                                    <summary>
                                        Complete Target Table Column Mapping ({viewModel.fullMappingRows.length} columns)
                                    </summary>
                                    <p className="empty-text mapping-note">
                                        This section shows the full target-table mapping, not just the single issue-focused column above.
                                    </p>
                                    {viewModel.fullMappingRows.length ? (
                                        <div className="table-wrap">
                                            <table className="mapping-table">
                                                <thead>
                                                    <tr>
                                                        <th>Old Column</th>
                                                        <th>New Column</th>
                                                        <th>Old Type</th>
                                                        <th>New Type</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {viewModel.fullMappingRows.map((row) => (
                                                        <tr key={`full-${row.old_column_name}-${row.new_column_name}`}>
                                                            <td>{row.old_column_name}</td>
                                                            <td>{row.new_column_name}</td>
                                                            <td>{row.data_type_old}</td>
                                                            <td>{row.data_type_new}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                        </div>
                                    ) : (
                                        <p className="empty-text">No full target-table mapping rows were returned.</p>
                                    )}
                                </details>
                            </article>

                            <section className="analysis-grid">
                                <div className="analysis-grid-header">
                                    <div>
                                        <p className="section-kicker">Script Comparison</p>
                                        <h2>Old vs New Script Analysis</h2>
                                    </div>
                                    <button
                                        type="button"
                                        className="toggle-evidence"
                                        onClick={() => setEvidenceExpanded((current) => !current)}
                                    >
                                        {evidenceExpanded ? "Hide Evidence and Script References" : "Show Evidence and Script References"}
                                    </button>
                                </div>
                                {viewModel.analyses.map((analysis) => (
                                    <AnalysisPanel
                                        key={analysis.title}
                                        title={analysis.title}
                                        observation={analysis.observation}
                                        data={analysis.data}
                                        evidenceExpanded={evidenceExpanded}
                                    />
                                ))}
                            </section>

                            <article className="panel">
                                <h2>Possible Resolutions</h2>
                                <SectionList
                                    title="Resolution Steps"
                                    items={viewModel.resolutions}
                                    emptyLabel="No resolutions were suggested."
                                />
                                <div className="meta-grid">
                                    <SectionList
                                        title="Evidence Gaps"
                                        items={viewModel.evidenceGaps}
                                        emptyLabel="No evidence gaps were reported."
                                    />
                                    <SectionList
                                        title="Unresolved Questions"
                                        items={viewModel.unresolvedQuestions}
                                        emptyLabel="No unresolved questions were reported."
                                    />
                                </div>
                                <SectionList
                                    title="Analysis Warnings"
                                    items={viewModel.analysisWarnings}
                                    emptyLabel="No analysis warnings were reported."
                                />
                            </article>
                        </>
                    )}

                    <details className="panel detail-block">
                        <summary>Formatted Summary</summary>
                        <pre className="summary-block">{viewModel.markdownSummary}</pre>
                    </details>

                    <details className="panel detail-block">
                        <summary>Raw Response</summary>
                        <pre className="json-block">{JSON.stringify(viewModel.raw, null, 2)}</pre>
                    </details>
                </section>
            ) : null}
        </>
    );
}

function DocsPage() {
    return (
        <section className="docs-stack">
            <section className="hero-card">
                <div className="hero-actions">
                    <div>
                        <p className="eyebrow">Project Docs</p>
                        <h1>Architecture and data flow for the Jira bug investigation POC</h1>
                        <p className="hero-copy">
                            This page documents how the UI, orchestrator, and three backend systems collaborate to
                            turn a Jira title into a grounded migration investigation summary.
                        </p>
                    </div>
                    <Link to="/" className="ghost nav-button">
                        Back To Investigation
                    </Link>
                </div>
            </section>

            <article className="panel docs-panel">
                <p className="section-kicker">Architecture</p>
                <h2>Service Responsibilities</h2>
                <figure className="docs-figure">
                    <img src="/docs-images/architecture-diagram.png" alt="Architecture diagram for the bug investigation platform" />
                    <figcaption>
                        High-level architecture showing the React UI, orchestrator, three backend systems, workbook inputs, script fixtures, and LLM analysis.
                    </figcaption>
                </figure>
                <div className="docs-card-grid">
                    {architectureHighlights.map((item) => (
                        <div key={item.title} className="docs-info-card">
                            <h3>{item.title}</h3>
                            <p>{item.description}</p>
                        </div>
                    ))}
                </div>
            </article>

            <article className="panel docs-panel">
                <p className="section-kicker">Data Flow</p>
                <h2>How a request moves through the system</h2>
                <figure className="docs-figure">
                    <img src="/docs-images/data-flow-diagram.png" alt="Data flow diagram for Jira title investigation" />
                    <figcaption>
                        End-to-end flow from Jira title input through parsing, metadata resolution, old/new script analysis, and final structured output.
                    </figcaption>
                </figure>
                <ol className="docs-flow-list">
                    <li>The user submits a Jira title from the UI.</li>
                    <li>The orchestrator calls System 1 to parse the title and classify the incident.</li>
                    <li>If the issue is data-related, System 2 resolves table metadata and old-to-new column mappings.</li>
                    <li>System 3 analyzes the old script and new script independently using the resolved mapping context.</li>
                    <li>The orchestrator returns a structured response that powers the investigation dashboard.</li>
                </ol>
            </article>

            <article className="panel docs-panel">
                <p className="section-kicker">Data Sources</p>
                <h2>Mock data used by the POC</h2>
                <div className="docs-card-grid">
                    {dataSources.map((item) => (
                        <div key={item.title} className="docs-info-card">
                            <h3>{item.title}</h3>
                            <p>{item.details}</p>
                        </div>
                    ))}
                </div>
            </article>

            <article className="panel docs-panel">
                <p className="section-kicker">Sample Data</p>
                <h2>Example workbook rows and script inputs</h2>
                <p className="hero-copy docs-copy">
                    This sample is taken from the <code>tentity_old</code> to <code>tentity_new</code> migration path.
                    It shows the kind of renamed-column mapping and old/new PySpark logic the investigation pipeline works with.
                </p>

                <section className="subsection">
                    <h3>Sample Column Mapping Sheet Rows</h3>
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
                                <h3>Old PySpark Example</h3>
                            </div>
                            <span className="metric-badge">tentity_old flow</span>
                        </div>
                        <pre className="code-block">{sampleOldScript}</pre>
                    </div>

                    <div className="docs-script-card">
                        <div className="docs-script-header">
                            <div>
                                <p className="section-kicker">Target Script</p>
                                <h3>New PySpark Example</h3>
                            </div>
                            <span className="metric-badge">tentity_new flow</span>
                        </div>
                        <pre className="code-block">{sampleNewScript}</pre>
                    </div>
                </section>
            </article>

            <article className="panel docs-panel">
                <p className="section-kicker">Output</p>
                <h2>What the analyst sees in the UI</h2>
                <ul className="detail-list">
                    {analystOutputs.map((item) => (
                        <li key={item}>{item}</li>
                    ))}
                </ul>
            </article>

            <article className="panel docs-panel">
                <p className="section-kicker">AI Layer</p>
                <h2>How AI is used in this POC</h2>
                <div className="docs-card-grid">
                    {aiUsageCards.map((item) => (
                        <div key={item.title} className="docs-info-card">
                            <h3>{item.title}</h3>
                            <p>{item.details}</p>
                        </div>
                    ))}
                </div>
                <div className="docs-card-grid">
                    <div className="docs-info-card">
                        <h3>Estimated Cost</h3>
                        <ul className="detail-list">
                            {aiCostNotes.map((item) => (
                                <li key={item}>{item}</li>
                            ))}
                        </ul>
                    </div>
                    <div className="docs-info-card">
                        <h3>Pricing Reference</h3>
                        <p>
                            Current pricing should be checked against the official OpenAI pricing page before using the
                            estimate operationally.
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
        </section>
    );
}

export default function App() {
    const [title, setTitle] = useState(sampleGroups[0].items[0]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [result, setResult] = useState(null);
    const [evidenceExpanded, setEvidenceExpanded] = useState(false);
    const [wakeState, setWakeState] = useState({
        status: "idle",
        startedAt: null,
        elapsedSeconds: 0,
    });

    const viewModel = useMemo(() => buildViewModel(result), [result]);

    useEffect(() => {
        if (wakeState.status !== "warming" || !wakeState.startedAt) {
            return undefined;
        }

        const intervalId = window.setInterval(() => {
            setWakeState((current) => {
                if (current.status !== "warming" || !current.startedAt) {
                    return current;
                }
                return {
                    ...current,
                    elapsedSeconds: Math.round((Date.now() - current.startedAt) / 1000),
                };
            });
        }, 1000);

        return () => window.clearInterval(intervalId);
    }, [wakeState.status, wakeState.startedAt]);

    async function handleSubmit(event) {
        event.preventDefault();
        setLoading(true);
        setError("");

        try {
            const response = await fetch(`${API_BASE_URL}/chat/investigate`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ raw_title: title }),
            });
            if (!response.ok) {
                const detail = await response.text();
                throw new Error(detail || "Request failed");
            }
            const payload = await response.json();
            setResult(payload);
            setEvidenceExpanded(false);
        } catch (submitError) {
            setError(submitError.message);
        } finally {
            setLoading(false);
        }
    }

    async function handleWakeBackend() {
        const startedAt = Date.now();
        setWakeState({
            status: "warming",
            startedAt,
            elapsedSeconds: 0,
        });

        try {
            const response = await fetch(`${API_BASE_URL}/warmup`, {
                method: "GET",
                headers: { "Cache-Control": "no-cache" },
            });
            if (!response.ok) {
                throw new Error("Backend warmup request failed.");
            }
            setWakeState({
                status: "ready",
                startedAt: null,
                elapsedSeconds: Math.round((Date.now() - startedAt) / 1000),
            });
        } catch (wakeError) {
            setWakeState({
                status: "failed",
                startedAt: null,
                elapsedSeconds: Math.round((Date.now() - startedAt) / 1000),
            });
            console.error(wakeError);
        }
    }

    return (
        <HashRouter>
            <main className="app-shell">
                <Routes>
                    <Route
                        path="/"
                        element={
                            <InvestigationPage
                                title={title}
                                setTitle={setTitle}
                                loading={loading}
                                error={error}
                                viewModel={viewModel}
                                evidenceExpanded={evidenceExpanded}
                                setEvidenceExpanded={setEvidenceExpanded}
                                handleSubmit={handleSubmit}
                                wakeState={wakeState}
                                handleWakeBackend={handleWakeBackend}
                            />
                        }
                    />
                    <Route path="/docs" element={<DocsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </main>
        </HashRouter>
    );
}
