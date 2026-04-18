import { useEffect, useMemo, useState } from "react";
import { HashRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import DocsPage from "./DocsPage";
import ObservabilityPage from "./ObservabilityPage";

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
            "OPS_TDUPSHIPMENT_Column ShipmentStatus duplicated in current target table",
            "TTY_TEVENTLOG_Column EventOccurredTs contains string date values",
            "FIN_TORDERLINK_Column SettlementStatusCode missing after join filter",
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
    const system4 = result.system4 || null;
    const isInfra = !system3;
    const fullMappingSource =
        system2.full_column_mapping ||
        system3?.system2?.full_column_mapping ||
        system2.column_mapping ||
        [];
    const fullMappingRows = dedupeMappingRows(fullMappingSource);

    return {
        isInfra,
        issueSummary: system4?.summary || system3?.final_summary || result.final_summary || system1.issue || "",
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
        sqlAnalysis: system4
            ? {
                targetTable: system4.target_table,
                scenarioType: formatLabel(system4.scenario_type),
                confidence: formatConfidence(system4.confidence),
                primaryQuery: system4.primary_query,
                diagnostics: system4.diagnostic_queries || [],
                issueFindings: system4.issue_findings || [],
                explanationPoints: system4.explanation_points || [],
                affectedCodeRefs: system4.affected_code_refs || [],
                warnings: system4.warnings || [],
            }
            : null,
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

function InvestigationAccordion({ badges = [], kicker, title, children }) {
    return (
        <details className="panel result-accordion">
            <summary className="result-accordion-summary">
                <div className="result-accordion-title">
                    <div>
                        <p className="section-kicker">{kicker}</p>
                        <h2>{title}</h2>
                    </div>
                    <div className="result-accordion-summary-side">
                        {badges.length ? (
                            <div className="metric-cluster result-accordion-badges">
                                {badges.map((badge) => (
                                    <span key={badge} className="metric-badge">
                                        {badge}
                                    </span>
                                ))}
                            </div>
                        ) : null}
                        <span className="result-accordion-chevron" aria-hidden="true" />
                    </div>
                </div>
            </summary>
            <div className="result-accordion-body">{children}</div>
        </details>
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

function renderCellValue(value) {
    if (value === null || value === undefined || value === "") {
        return "NULL";
    }
    if (typeof value === "object") {
        return JSON.stringify(value);
    }
    return String(value);
}

function QueryResultPanel({ title, purpose, result, findings }) {
    const rows = result?.rows || [];
    const columns = result?.columns || [];

    return (
        <article className="query-card">
            <div className="query-header">
                <div>
                    <p className="section-kicker">{title}</p>
                    <h3>{result?.label || title}</h3>
                </div>
                <span className="metric-badge">Rows: {result?.row_count ?? 0}</span>
            </div>
            <p className="analysis-summary">{purpose}</p>
            <pre className="code-block query-sql">{result?.sql || "No SQL query was executed."}</pre>
            {rows.length && columns.length ? (
                <div className="table-wrap">
                    <table className="mapping-table">
                        <thead>
                            <tr>
                                {columns.map((column) => (
                                    <th key={`${title}-${column}`}>{column}</th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {rows.map((row, rowIndex) => (
                                <tr key={`${title}-row-${rowIndex}`}>
                                    {columns.map((column) => (
                                        <td key={`${title}-${rowIndex}-${column}`}>{renderCellValue(row[column])}</td>
                                    ))}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            ) : (
                <p className="empty-text">This query did not return any rows.</p>
            )}
            {findings?.length ? <SectionList title="Query Findings" items={findings} emptyLabel="No query findings recorded." /> : null}
        </article>
    );
}

function SqlAnalysisPanel({ sqlAnalysis }) {
    if (!sqlAnalysis) {
        return <p className="empty-text">No SQL analysis was produced for this issue.</p>;
    }

    return (
        <div className="sql-grid">
            <article className="panel sql-summary-panel">
                <div className="stats-grid">
                    <div className="stat-card">
                        <span className="stat-label">Target Table</span>
                        <strong className="stat-value">{sqlAnalysis.targetTable}</strong>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Primary Query Rows</span>
                        <strong className="stat-value">{sqlAnalysis.primaryQuery?.row_count ?? 0}</strong>
                    </div>
                </div>
                <div className="meta-grid">
                    <SectionList title="SQL Findings" items={sqlAnalysis.issueFindings} emptyLabel="No SQL findings were produced." />
                    <SectionList
                        title="Comparison Summary"
                        items={sqlAnalysis.explanationPoints}
                        emptyLabel="No SQL comparison points were produced."
                    />
                </div>
                <SectionList title="Warnings" items={sqlAnalysis.warnings} emptyLabel="No SQL warnings were produced." />
            </article>

            <QueryResultPanel
                title="Primary SQL Query"
                purpose="This query fetches the current target-table rows related to the issue keys."
                result={sqlAnalysis.primaryQuery}
                findings={[]}
            />

            <div className="sql-diagnostic-stack">
                {sqlAnalysis.diagnostics.map((diagnostic) => (
                    <QueryResultPanel
                        key={`${diagnostic.name}-${diagnostic.query?.sql}`}
                        title={diagnostic.name}
                        purpose={diagnostic.purpose}
                        result={diagnostic.query}
                        findings={diagnostic.findings}
                    />
                ))}
            </div>

            <article className="panel">
                <SectionList title="Affected New-Script Code References" items={null} emptyLabel="No new-script references were selected.">
                    {sqlAnalysis.affectedCodeRefs?.length ? (
                        <div className="evidence-stack">
                            {sqlAnalysis.affectedCodeRefs.map((item, index) => (
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
                        <p className="empty-text">No new-script references were selected.</p>
                    )}
                </SectionList>
            </article>
        </div>
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
                            mapping, old and new script analysis, SQL diagnostics, and recommended next steps in a structured dashboard.
                        </p>
                    </div>
                    <div className="hero-side-actions">
                        <Link to="/observability" className="ghost nav-button">
                            Monitoring
                        </Link>
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
                            <InvestigationAccordion
                                kicker="Target Table Mapping"
                                title="Issue-Focused Column Mapping"
                                badges={["All rows treated as renamed"]}
                            >
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
                            </InvestigationAccordion>

                            <InvestigationAccordion kicker="Script Comparison" title="Old vs New Script Analysis">
                                {viewModel.findings.length ? (
                                    <div className="findings-grid">
                                        {viewModel.findings.map((item) => (
                                            <div key={item.label} className="finding-card">
                                                <span className="stat-label">{item.label}</span>
                                                <p>{item.value || "N/A"}</p>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="empty-text">No script findings were produced.</p>
                                )}
                                <div className="accordion-section-toolbar">
                                    <button
                                        type="button"
                                        className="toggle-evidence"
                                        onClick={() => setEvidenceExpanded((current) => !current)}
                                    >
                                        {evidenceExpanded ? "Hide Evidence and Script References" : "Show Evidence and Script References"}
                                    </button>
                                </div>
                                <section className="analysis-grid">
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
                            </InvestigationAccordion>

                            <InvestigationAccordion
                                kicker="System 4"
                                title="SQL Data vs New Script Impact"
                                badges={[
                                    `Scenario: ${viewModel.sqlAnalysis?.scenarioType || "N/A"}`,
                                    `Confidence: ${viewModel.sqlAnalysis?.confidence || "N/A"}`,
                                ]}
                            >
                                <SqlAnalysisPanel sqlAnalysis={viewModel.sqlAnalysis} />
                            </InvestigationAccordion>

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
                    <Route path="/observability" element={<ObservabilityPage apiBaseUrl={API_BASE_URL} />} />
                    <Route path="/docs" element={<DocsPage />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </main>
        </HashRouter>
    );
}
