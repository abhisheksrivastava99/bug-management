import { startTransition, useDeferredValue, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

const statusOrder = ["Failed", "Cancelled", "InProgress", "Succeeded"];
const querySuggestions = [
    "Which weekly pipelines are getting slower?",
    "Show success rate by pipeline for the last 30 days",
    "Which pipelines had retries recently?",
    "Show recent failures across all cadences",
];

const cadenceOptions = [
    { label: "All Cadences", value: "" },
    { label: "Daily", value: "daily" },
    { label: "Weekly", value: "weekly" },
    { label: "Monthly", value: "monthly" },
];

const statusOptions = [
    { label: "All Statuses", value: "" },
    { label: "Failed", value: "Failed" },
    { label: "Cancelled", value: "Cancelled" },
    { label: "In Progress", value: "InProgress" },
    { label: "Succeeded", value: "Succeeded" },
];

export default function ObservabilityPage({ apiBaseUrl }) {
    const [filters, setFilters] = useState({
        windowDays: 30,
        cadence: "",
        status: "",
        owner: "",
        criticality: "",
        search: "",
    });
    const [summary, setSummary] = useState(null);
    const [pipelines, setPipelines] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [ownerOptions, setOwnerOptions] = useState([]);
    const [criticalityOptions, setCriticalityOptions] = useState([]);
    const [selectedPipelineName, setSelectedPipelineName] = useState("");
    const [detail, setDetail] = useState(null);
    const [detailLoading, setDetailLoading] = useState(false);
    const [detailError, setDetailError] = useState("");
    const [aiSummary, setAiSummary] = useState(null);
    const [aiSummaryLoading, setAiSummaryLoading] = useState(false);
    const [aiSummaryError, setAiSummaryError] = useState("");
    const [queryText, setQueryText] = useState(querySuggestions[0]);
    const [queryResponse, setQueryResponse] = useState(null);
    const [queryLoading, setQueryLoading] = useState(false);
    const [queryError, setQueryError] = useState("");
    const deferredSearch = useDeferredValue(filters.search);

    const effectiveFilters = useMemo(
        () => ({
            ...filters,
            search: deferredSearch,
        }),
        [filters, deferredSearch],
    );

    useEffect(() => {
        let isCancelled = false;
        setLoading(true);
        setError("");

        Promise.all([
            fetchJson(`${apiBaseUrl}/observability/summary?${buildQueryParams(effectiveFilters)}`),
            fetchJson(`${apiBaseUrl}/observability/pipelines?${buildQueryParams(effectiveFilters)}`),
        ])
            .then(([summaryPayload, pipelinesPayload]) => {
                if (isCancelled) {
                    return;
                }
                startTransition(() => {
                    setSummary(summaryPayload);
                    setPipelines(pipelinesPayload);
                    setOwnerOptions((current) => mergeOptions(current, collectDistinctValues(pipelinesPayload.groups, "owner")));
                    setCriticalityOptions((current) =>
                        mergeOptions(current, collectDistinctValues(pipelinesPayload.groups, "criticality")),
                    );
                });
            })
            .catch((loadError) => {
                if (!isCancelled) {
                    setError(loadError.message || "Unable to load the observability dashboard.");
                }
            })
            .finally(() => {
                if (!isCancelled) {
                    setLoading(false);
                }
            });

        return () => {
            isCancelled = true;
        };
    }, [apiBaseUrl, effectiveFilters]);

    useEffect(() => {
        if (!selectedPipelineName) {
            setDetail(null);
            setDetailError("");
            return undefined;
        }

        let isCancelled = false;
        setDetailLoading(true);
        setDetailError("");

        fetchJson(
            `${apiBaseUrl}/observability/pipelines/${encodeURIComponent(selectedPipelineName)}?${buildQueryParams(effectiveFilters)}`,
        )
            .then((payload) => {
                if (!isCancelled) {
                    startTransition(() => {
                        setDetail(payload);
                    });
                }
            })
            .catch((loadError) => {
                if (!isCancelled) {
                    setDetailError(loadError.message || "Unable to load pipeline details.");
                }
            })
            .finally(() => {
                if (!isCancelled) {
                    setDetailLoading(false);
                }
            });

        return () => {
            isCancelled = true;
        };
    }, [apiBaseUrl, effectiveFilters, selectedPipelineName]);

    const groups = pipelines?.groups || [];
    const visiblePipelines = useMemo(() => flattenVisiblePipelines(groups), [groups]);
    const emptyState = !loading && !error && groups.every((group) => group.pipelines.length === 0);

    async function handleGenerateAiSummary() {
        if (!summary || !groups.length) {
            return;
        }
        setAiSummaryLoading(true);
        setAiSummaryError("");
        try {
            const payload = await fetchJson(`${apiBaseUrl}/observability/summary-ai`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ summary, groups }),
            });
            setAiSummary(payload);
        } catch (summaryError) {
            setAiSummaryError(summaryError.message || "Unable to generate the AI summary.");
        } finally {
            setAiSummaryLoading(false);
        }
    }

    async function handleRunQuery(event) {
        event.preventDefault();
        if (!queryText.trim()) {
            return;
        }
        setQueryLoading(true);
        setQueryError("");
        try {
            const payload = await fetchJson(`${apiBaseUrl}/observability/query`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    question: queryText,
                    filters: toApiFilters(effectiveFilters),
                }),
            });
            setQueryResponse(payload);
        } catch (submitError) {
            setQueryError(submitError.message || "Unable to run the AI query.");
        } finally {
            setQueryLoading(false);
        }
    }

    function handleFilterChange(field, value) {
        setFilters((current) => ({ ...current, [field]: value }));
    }

    return (
        <section className="monitoring-stack">
            <section className="hero-card">
                <div className="hero-actions">
                    <div>
                        <p className="eyebrow">Azure Observability POC</p>
                        <h1>Monitor scheduled Azure pipelines in one operational dashboard</h1>
                        <p className="hero-copy">
                            Review the pipelines that need action first, compare daily, weekly, and monthly health,
                            then drill into run history and activity patterns without leaving the page.
                        </p>
                    </div>
                    <div className="hero-side-actions">
                        <Link to="/" className="ghost nav-button">
                            Investigation
                        </Link>
                        <Link to="/docs" className="ghost nav-button">
                            Open Docs
                        </Link>
                    </div>
                </div>
            </section>

            <section className="panel">
                <div className="section-heading">
                    <div>
                        <p className="section-kicker">Filters</p>
                        <h2>Dashboard Scope</h2>
                    </div>
                    <span className="metric-badge">Default window: last 30 days</span>
                </div>
                <div className="filter-grid">
                    <label>
                        Time Window
                        <select value={filters.windowDays} onChange={(event) => handleFilterChange("windowDays", Number(event.target.value))}>
                            <option value={30}>30 days</option>
                            <option value={60}>60 days</option>
                            <option value={90}>90 days</option>
                        </select>
                    </label>
                    <label>
                        Cadence
                        <select value={filters.cadence} onChange={(event) => handleFilterChange("cadence", event.target.value)}>
                            {cadenceOptions.map((option) => (
                                <option key={option.value || "all"} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Status
                        <select value={filters.status} onChange={(event) => handleFilterChange("status", event.target.value)}>
                            {statusOptions.map((option) => (
                                <option key={option.value || "all"} value={option.value}>
                                    {option.label}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Owner
                        <select value={filters.owner} onChange={(event) => handleFilterChange("owner", event.target.value)}>
                            <option value="">All Owners</option>
                            {ownerOptions.map((option) => (
                                <option key={option} value={option}>
                                    {option}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label>
                        Criticality
                        <select value={filters.criticality} onChange={(event) => handleFilterChange("criticality", event.target.value)}>
                            <option value="">All Criticalities</option>
                            {criticalityOptions.map((option) => (
                                <option key={option} value={option}>
                                    {formatLabel(option)}
                                </option>
                            ))}
                        </select>
                    </label>
                    <label className="filter-search">
                        Pipeline Search
                        <input
                            type="search"
                            value={filters.search}
                            onChange={(event) => handleFilterChange("search", event.target.value)}
                            placeholder="Search pipeline name"
                        />
                    </label>
                </div>
            </section>

            {error ? <section className="panel error-box">{error}</section> : null}
            {loading ? <section className="panel">Loading observability dashboard...</section> : null}

            {!loading && summary ? (
                <>
                    <section className="panel">
                        <div className="section-heading">
                            <div>
                                <p className="section-kicker">Pipelines</p>
                                <h2>What Needs Eyes Right Now</h2>
                            </div>
                            <span className="metric-badge">{summary.attention_items.length} active signals</span>
                        </div>
                        {summary.attention_items.length ? (
                            <div className="attention-grid">
                                {summary.attention_items.map((item) => (
                                    <article key={`${item.kind}-${item.pipeline_name}`} className={`attention-card tone-${item.attention_state}`}>
                                        <div className="attention-meta">
                                            <span className="section-kicker">{formatLabel(item.kind)}</span>
                                            <span className={`status-pill status-${item.status}`}>{item.status}</span>
                                        </div>
                                        <h3>{item.pipeline_name}</h3>
                                        <p>{item.description}</p>
                                        <button
                                            type="button"
                                            className="ghost nav-button attention-action"
                                            onClick={() => setSelectedPipelineName(item.pipeline_name)}
                                        >
                                            View Details
                                        </button>
                                    </article>
                                ))}
                            </div>
                        ) : (
                            <p className="empty-text">No pipelines need attention in the current filters.</p>
                        )}
                    </section>

                    <section className="panel">
                        <div className="section-heading">
                            <div>
                                <p className="section-kicker">Summary Band</p>
                                <h2>Current Operational Snapshot</h2>
                            </div>
                            <span className="metric-badge">Dashboard-first view</span>
                        </div>
                        <div className="stats-grid">
                            {summary.summary_metrics.map((metric) => (
                                <div key={metric.label} className={`stat-card tone-${metric.tone}`}>
                                    <span className="stat-label">{metric.label}</span>
                                    <strong className="stat-value">{metric.value}</strong>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="panel">
                        <div className="section-heading">
                            <div>
                                <p className="section-kicker">Ops Overview</p>
                                <h2>Pipeline Graphs</h2>
                            </div>
                            <span className="metric-badge">4 graphs</span>
                        </div>
                        <PipelineOverviewCharts
                            groups={groups}
                            summary={summary}
                            visiblePipelines={visiblePipelines}
                            onOpenPipeline={setSelectedPipelineName}
                        />
                    </section>

                    <section className="panel ai-summary-panel">
                        <div className="section-heading">
                            <div>
                                <p className="section-kicker">AI Summary</p>
                                <h2>Optional Natural-Language Snapshot</h2>
                            </div>
                            <button type="button" className="ghost nav-button" onClick={handleGenerateAiSummary} disabled={aiSummaryLoading}>
                                {aiSummaryLoading ? "Generating..." : aiSummary ? "Refresh Summary" : "Generate Summary"}
                            </button>
                        </div>
                        {aiSummaryError ? <p className="empty-text">{aiSummaryError}</p> : null}
                        {aiSummary ? (
                            <div className="ai-summary-card">
                                <h3>{aiSummary.title}</h3>
                                <p className="analysis-summary">{aiSummary.summary}</p>
                                <ul className="detail-list">
                                    {aiSummary.insights.map((insight) => (
                                        <li key={insight}>{insight}</li>
                                    ))}
                                </ul>
                                {aiSummary.caveat ? <p className="empty-text">{aiSummary.caveat}</p> : null}
                            </div>
                        ) : (
                            <p className="empty-text">Generate this card on demand to keep the dashboard fast and deterministic by default.</p>
                        )}
                    </section>

                    <details className="panel ai-panel">
                        <summary>AI Query Assistant</summary>
                        <form onSubmit={handleRunQuery} className="query-form">
                            <label htmlFor="observability-query">Ask a question in plain English</label>
                            <textarea
                                id="observability-query"
                                rows={3}
                                value={queryText}
                                onChange={(event) => setQueryText(event.target.value)}
                                placeholder="Which weekly pipelines are getting slower?"
                            />
                            <div className="toolbar">
                                <button type="submit" disabled={queryLoading || !queryText.trim()}>
                                    {queryLoading ? "Running..." : "Run AI Query"}
                                </button>
                                <div className="sample-list">
                                    {querySuggestions.map((suggestion) => (
                                        <button key={suggestion} type="button" className="ghost" onClick={() => setQueryText(suggestion)}>
                                            {suggestion}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        </form>
                        {queryError ? <p className="empty-text">{queryError}</p> : null}
                        {queryResponse ? <AiQueryResult response={queryResponse} onOpenPipeline={setSelectedPipelineName} /> : null}
                    </details>

                    {emptyState ? (
                        <section className="panel">
                            <p className="empty-text">No pipelines match the current filters.</p>
                        </section>
                    ) : (
                        groups.map((group) => (
                            <section key={group.cadence} className="panel pipeline-section">
                                <div className="section-heading">
                                    <div>
                                        <p className="section-kicker">{group.label}</p>
                                        <h2>{group.label} Pipelines</h2>
                                    </div>
                                    <div className="metric-cluster">
                                        <span className="metric-badge">{group.total_count} pipelines</span>
                                        <span className="metric-badge">{group.attention_count} needing attention</span>
                                    </div>
                                </div>
                                {group.pipelines.length ? (
                                    <div className="table-wrap">
                                        <table className="pipeline-table">
                                            <thead>
                                                <tr>
                                                    <th>Pipeline</th>
                                                    <th>Owner</th>
                                                    <th>Criticality</th>
                                                    <th>Last Run</th>
                                                    <th>Last Duration</th>
                                                    <th>Avg Last 7</th>
                                                    <th>Trend</th>
                                                    <th>Success Rate</th>
                                                    <th>Attention</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                {group.pipelines.map((row) => (
                                                    <tr key={row.pipeline_name}>
                                                        <td>
                                                            <button
                                                                type="button"
                                                                className="table-link"
                                                                onClick={() => setSelectedPipelineName(row.pipeline_name)}
                                                            >
                                                                {row.pipeline_name}
                                                            </button>
                                                            <div className="table-subtext">{row.business_domain}</div>
                                                        </td>
                                                        <td>{row.owner}</td>
                                                        <td>{formatLabel(row.criticality)}</td>
                                                        <td>
                                                            <span className={`status-pill status-${row.last_run_status}`}>{row.last_run_status}</span>
                                                            <div className="table-subtext">{formatDateTime(row.last_run_start)}</div>
                                                        </td>
                                                        <td>{formatDuration(row.last_run_duration_seconds)}</td>
                                                        <td>{formatDuration(row.average_duration_last_7_runs)}</td>
                                                        <td>
                                                            <span className={`trend-pill ${trendClassName(row.duration_delta_pct)}`}>
                                                                {formatTrend(row.duration_delta_pct)}
                                                            </span>
                                                        </td>
                                                        <td>{formatPercent(row.success_rate_window)}</td>
                                                        <td>
                                                            <span className={`attention-pill tone-${row.attention_state}`}>{row.attention_reason}</span>
                                                        </td>
                                                    </tr>
                                                ))}
                                            </tbody>
                                        </table>
                                    </div>
                                ) : (
                                    <p className="empty-text">No {group.label.toLowerCase()} pipelines match the current filters.</p>
                                )}
                            </section>
                        ))
                    )}
                </>
            ) : null}

            {selectedPipelineName ? (
                <div className="drawer-backdrop" onClick={() => setSelectedPipelineName("")}>
                    <aside className="detail-drawer" onClick={(event) => event.stopPropagation()}>
                        <div className="drawer-header">
                            <div>
                                <p className="section-kicker">Pipeline Detail</p>
                                <h2>{selectedPipelineName}</h2>
                            </div>
                            <button type="button" className="ghost nav-button" onClick={() => setSelectedPipelineName("")}>
                                Close
                            </button>
                        </div>
                        {detailLoading ? <p className="empty-text">Loading pipeline detail...</p> : null}
                        {detailError ? <p className="empty-text">{detailError}</p> : null}
                        {detail ? <PipelineDetailDrawer detail={detail} /> : null}
                    </aside>
                </div>
            ) : null}
        </section>
    );
}

function PipelineOverviewCharts({ groups, summary, visiblePipelines, onOpenPipeline }) {
    return (
        <div className="graph-band">
            <div className="graph-grid">
                <CadenceHealthChart groups={groups} />
                <PipelineSuccessRateChart pipelines={visiblePipelines} onOpenPipeline={onOpenPipeline} />
                <DurationRegressionChart pipelines={summary.top_regressions || []} onOpenPipeline={onOpenPipeline} />
                <RecentFailuresChart failures={summary.recent_failures || []} onOpenPipeline={onOpenPipeline} />
            </div>
        </div>
    );
}

function CadenceHealthChart({ groups }) {
    const totalVisible = groups.reduce((sum, group) => sum + group.total_count, 0);

    return (
        <article className="graph-card graph-card-emphasis">
            <div className="graph-card-header">
                <div>
                    <p className="section-kicker">Health</p>
                    <h3>Cadence Health</h3>
                </div>
                <span className="metric-badge">{totalVisible} visible</span>
            </div>
            <div className="graph-legend">
                <span className="legend-item">
                    <span className="legend-swatch legend-swatch-healthy" />
                    Healthy
                </span>
                <span className="legend-item">
                    <span className="legend-swatch legend-swatch-attention" />
                    Needing attention
                </span>
            </div>
            <div className="cadence-health-list">
                {groups.map((group) => {
                    const healthyCount = Math.max(0, group.total_count - group.attention_count);
                    return (
                        <div key={group.cadence} className="cadence-health-card">
                            <div className="cadence-health-topline">
                                <strong>{group.label}</strong>
                                <span>{group.total_count} total</span>
                            </div>
                            <div className="stacked-bar-track cadence-health-track" aria-label={`${group.label} pipeline health`}>
                                {group.total_count ? (
                                    <>
                                        <span
                                            className="stacked-bar-segment stacked-bar-segment-healthy"
                                            style={{ width: stackedBarWidth(healthyCount, group.total_count) }}
                                        />
                                        <span
                                            className="stacked-bar-segment stacked-bar-segment-attention"
                                            style={{ width: stackedBarWidth(group.attention_count, group.total_count) }}
                                        />
                                    </>
                                ) : (
                                    <span className="stacked-bar-empty" />
                                )}
                            </div>
                            <div className="cadence-health-meta">
                                <span>{healthyCount} healthy</span>
                                <span>{group.attention_count} attention</span>
                            </div>
                        </div>
                    );
                })}
            </div>
        </article>
    );
}

function PipelineSuccessRateChart({ pipelines, onOpenPipeline }) {
    const sortedPipelines = [...pipelines]
        .sort(
            (left, right) =>
                safeNumber(left.success_rate_window, 101) - safeNumber(right.success_rate_window, 101) ||
                left.pipeline_name.localeCompare(right.pipeline_name),
        )
        .slice(0, 5);

    return (
        <article className="graph-card graph-card-emphasis">
            <div className="graph-card-header">
                <div>
                    <p className="section-kicker">Reliability</p>
                    <h3>Pipeline Success Rate</h3>
                </div>
                <span className="metric-badge">{sortedPipelines.length} shown</span>
            </div>
            {sortedPipelines.length ? (
                <div className="column-chart">
                    <div className="column-chart-scale" aria-hidden="true">
                        <span>100%</span>
                        <span>50%</span>
                        <span>0%</span>
                    </div>
                    <div className="column-chart-plot">
                        {sortedPipelines.map((pipeline) => (
                            <button
                                key={pipeline.pipeline_name}
                                type="button"
                                className="chart-column"
                                onClick={() => onOpenPipeline(pipeline.pipeline_name)}
                                title={formatPipelineDisplayName(pipeline.pipeline_name)}
                            >
                                <span className="chart-column-value">{formatPercent(pipeline.success_rate_window)}</span>
                                <span className="chart-column-bar-shell">
                                    <span
                                        className={`chart-column-bar ${successRateFillClassName(pipeline.success_rate_window)}`}
                                        style={{ height: percentBarWidth(pipeline.success_rate_window) }}
                                    />
                                </span>
                                <span className="chart-column-label">{formatPipelineDisplayName(pipeline.pipeline_name)}</span>
                                <span className="chart-column-meta">{formatLabel(pipeline.cadence)}</span>
                            </button>
                        ))}
                    </div>
                </div>
            ) : (
                <p className="empty-text graph-empty">No visible pipelines are available in the current view.</p>
            )}
        </article>
    );
}

function DurationRegressionChart({ pipelines, onOpenPipeline }) {
    const regressions = [...pipelines]
        .filter((pipeline) => safeNumber(pipeline.duration_delta_pct, 0) > 0)
        .sort(
            (left, right) =>
                safeNumber(right.duration_delta_pct, 0) - safeNumber(left.duration_delta_pct, 0) ||
                left.pipeline_name.localeCompare(right.pipeline_name),
        )
        .slice(0, 5);
    const maxDelta = Math.max(...regressions.map((pipeline) => safeNumber(pipeline.duration_delta_pct)), 1);

    return (
        <article className="graph-card graph-card-emphasis">
            <div className="graph-card-header">
                <div>
                    <p className="section-kicker">Performance</p>
                    <h3>Duration Regressions</h3>
                </div>
                <span className="metric-badge">{regressions.length} shown</span>
            </div>
            {regressions.length ? (
                <div className="column-chart">
                    <div className="column-chart-scale" aria-hidden="true">
                        <span>{formatTrend(maxDelta)}</span>
                        <span>Mid</span>
                        <span>0</span>
                    </div>
                    <div className="column-chart-plot">
                        {regressions.map((pipeline) => (
                            <button
                                key={pipeline.pipeline_name}
                                type="button"
                                className="chart-column"
                                onClick={() => onOpenPipeline(pipeline.pipeline_name)}
                                title={formatPipelineDisplayName(pipeline.pipeline_name)}
                            >
                                <span className="chart-column-value">{formatTrend(pipeline.duration_delta_pct)}</span>
                                <span className="chart-column-bar-shell">
                                    <span
                                        className={`chart-column-bar chart-column-bar-regression ${regressionFillClassName(
                                            pipeline.duration_delta_pct,
                                        )}`}
                                        style={{ height: scaledBarWidth(pipeline.duration_delta_pct, maxDelta) }}
                                    />
                                </span>
                                <span className="chart-column-label">{formatPipelineDisplayName(pipeline.pipeline_name)}</span>
                                <span className="chart-column-meta">{formatLabel(pipeline.cadence)}</span>
                            </button>
                        ))}
                    </div>
                </div>
            ) : (
                <p className="empty-text graph-empty">No duration regressions are active in the current view.</p>
            )}
        </article>
    );
}

function RecentFailuresChart({ failures, onOpenPipeline }) {
    const recentFailures = [...failures]
        .sort((left, right) => new Date(right.started_at) - new Date(left.started_at))
        .slice(0, 5);

    return (
        <article className="graph-card graph-card-emphasis">
            <div className="graph-card-header">
                <div>
                    <p className="section-kicker">Failures</p>
                    <h3>Recent Failures</h3>
                </div>
                <span className="metric-badge">{recentFailures.length} in scope</span>
            </div>
            {recentFailures.length ? (
                <ol className="failure-rail">
                    {recentFailures.map((failure) => (
                        <li key={`${failure.pipeline_name}-${failure.started_at}`} className="failure-rail-row">
                            <span className={`timeline-dot ${timelineDotClassName(failure.status)}`} aria-hidden="true" />
                            <button
                                type="button"
                                className="failure-rail-card"
                                onClick={() => onOpenPipeline(failure.pipeline_name)}
                                title={formatPipelineDisplayName(failure.pipeline_name)}
                            >
                                <span className="failure-rail-topline">
                                    <span className="failure-rail-name">{formatPipelineDisplayName(failure.pipeline_name)}</span>
                                    <span className={`status-pill failure-rail-status status-${failure.status}`}>{failure.status}</span>
                                </span>
                                <span className="failure-rail-meta">{formatDateTime(failure.started_at)}</span>
                                <span className="failure-rail-cadence">{formatLabel(failure.cadence)}</span>
                            </button>
                        </li>
                    ))}
                </ol>
            ) : (
                <p className="empty-text graph-empty">No failed runs landed in the current filter window.</p>
            )}
        </article>
    );
}

function PipelineDetailDrawer({ detail }) {
    return (
        <div className="drawer-stack">
            <section className="panel drawer-panel">
                <div className="stats-grid">
                    <div className="stat-card">
                        <span className="stat-label">Last Run Status</span>
                        <strong className="stat-value">{detail.pipeline.last_run_status}</strong>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Last Run Duration</span>
                        <strong className="stat-value">{formatDuration(detail.pipeline.last_run_duration_seconds)}</strong>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Avg Last 7</span>
                        <strong className="stat-value">{formatDuration(detail.pipeline.average_duration_last_7_runs)}</strong>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Success Rate</span>
                        <strong className="stat-value">{formatPercent(detail.pipeline.success_rate_window)}</strong>
                    </div>
                </div>
            </section>

            <section className="panel drawer-panel">
                <h3>Attention Signals</h3>
                {detail.attention_items.length ? (
                    <div className="attention-grid compact">
                        {detail.attention_items.map((item) => (
                            <article key={`${item.kind}-${item.pipeline_name}`} className={`attention-card compact tone-${item.attention_state}`}>
                                <div className="attention-meta">
                                    <span className="section-kicker">{formatLabel(item.kind)}</span>
                                    <span className={`status-pill status-${item.status}`}>{item.status}</span>
                                </div>
                                <p>{item.description}</p>
                            </article>
                        ))}
                    </div>
                ) : (
                    <p className="empty-text">No attention signals for this pipeline in the current view.</p>
                )}
            </section>

            <section className="panel drawer-panel">
                <h3>Duration Trend</h3>
                <div className="mini-chart">
                    {detail.duration_trend.map((point) => (
                        <div key={`${point.start}-${point.label}`} className="mini-chart-row">
                            <span className="mini-chart-label">{point.label}</span>
                            <div className="mini-chart-track">
                                <div
                                    className={`mini-chart-fill status-${point.status}`}
                                    style={{ width: `${Math.max(8, scaleDuration(point.duration_seconds, detail.duration_trend))}%` }}
                                />
                            </div>
                            <span className="mini-chart-value">{formatDuration(point.duration_seconds)}</span>
                        </div>
                    ))}
                </div>
            </section>

            <section className="panel drawer-panel">
                <div className="section-heading">
                    <div>
                        <p className="section-kicker">Latest Failure</p>
                        <h3>Failure Context</h3>
                    </div>
                </div>
                {detail.latest_failure ? (
                    <div className="failure-card">
                        <span className={`status-pill status-${detail.latest_failure.status}`}>{detail.latest_failure.status}</span>
                        <p>{detail.latest_failure.error_message || "No error message recorded."}</p>
                        <p className="table-subtext">{formatDateTime(detail.latest_failure.start)}</p>
                    </div>
                ) : (
                    <p className="empty-text">No failed or cancelled runs are available for this pipeline.</p>
                )}
            </section>

            <section className="panel drawer-panel">
                <h3>Retry Summary</h3>
                <div className="stats-grid">
                    <div className="stat-card">
                        <span className="stat-label">Retries In Scope</span>
                        <strong className="stat-value">{detail.retry_summary.total_retries}</strong>
                    </div>
                    <div className="stat-card">
                        <span className="stat-label">Latest Retry</span>
                        <strong className="stat-value">{formatDateTime(detail.retry_summary.latest_retry_at)}</strong>
                    </div>
                </div>
                {detail.retry_summary.recent_retry_runs.length ? (
                    <ul className="detail-list">
                        {detail.retry_summary.recent_retry_runs.map((run) => (
                            <li key={run.run_id}>
                                {formatDateTime(run.start)} · {run.status} · {formatDuration(run.duration_seconds)}
                            </li>
                        ))}
                    </ul>
                ) : (
                    <p className="empty-text">No retry runs are in the current detail window.</p>
                )}
            </section>

            <section className="panel drawer-panel">
                <h3>Recent Run History</h3>
                <div className="table-wrap">
                    <table className="pipeline-table compact-table">
                        <thead>
                            <tr>
                                <th>Status</th>
                                <th>Trigger</th>
                                <th>Started</th>
                                <th>Duration</th>
                                <th>Retry</th>
                            </tr>
                        </thead>
                        <tbody>
                            {detail.run_history.map((run) => (
                                <tr key={run.run_id}>
                                    <td>
                                        <span className={`status-pill status-${run.status}`}>{run.status}</span>
                                    </td>
                                    <td>{run.trigger_type}</td>
                                    <td>{formatDateTime(run.start)}</td>
                                    <td>{formatDuration(run.duration_seconds)}</td>
                                    <td>{run.retry_attempt}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </section>

            <section className="panel drawer-panel">
                <h3>Activity Summary</h3>
                {detail.activity_summary.length ? (
                    <div className="table-wrap">
                        <table className="pipeline-table compact-table">
                            <thead>
                                <tr>
                                    <th>Activity</th>
                                    <th>Type</th>
                                    <th>Latest Status</th>
                                    <th>Avg Duration</th>
                                    <th>Failures</th>
                                </tr>
                            </thead>
                            <tbody>
                                {detail.activity_summary.map((item) => (
                                    <tr key={`${item.activity_name}-${item.activity_type}`}>
                                        <td>{item.activity_name}</td>
                                        <td>{item.activity_type}</td>
                                        <td>
                                            <span className={`status-pill status-${item.latest_status}`}>{item.latest_status}</span>
                                        </td>
                                        <td>{formatDuration(item.average_duration_seconds)}</td>
                                        <td>{item.failure_count}</td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="empty-text">No activity rollups are available for this pipeline yet.</p>
                )}
            </section>
        </div>
    );
}

function AiQueryResult({ response, onOpenPipeline }) {
    const pipelineField = response.result.columns.find((column) => column === "pipeline_name");

    return (
        <section className="query-result-grid">
            <article className="panel">
                <div className="section-heading">
                    <div>
                        <p className="section-kicker">Query Summary</p>
                        <h3>{response.summary}</h3>
                    </div>
                    {response.used_fallback ? <span className="metric-badge">Fallback Mode</span> : null}
                </div>
                <ul className="detail-list">
                    {response.insights.map((insight) => (
                        <li key={insight}>{insight}</li>
                    ))}
                </ul>
                {response.caveats.length ? (
                    <div className="subsection">
                        <h4>Caveats</h4>
                        <ul className="detail-list">
                            {response.caveats.map((caveat) => (
                                <li key={caveat}>{caveat}</li>
                            ))}
                        </ul>
                    </div>
                ) : null}
                {response.follow_ups.length ? (
                    <div className="subsection">
                        <h4>Suggested Follow-Ups</h4>
                        <ul className="detail-list">
                            {response.follow_ups.map((followUp) => (
                                <li key={followUp}>{followUp}</li>
                            ))}
                        </ul>
                    </div>
                ) : null}
            </article>

            <article className="panel">
                <div className="section-heading">
                    <div>
                        <p className="section-kicker">Results</p>
                        <h3>{response.result.row_count} Rows Returned</h3>
                    </div>
                    <span className="metric-badge">{formatLabel(response.query_plan.intent)}</span>
                </div>
                {response.result.rows.length ? (
                    <div className="table-wrap">
                        <table className="pipeline-table compact-table">
                            <thead>
                                <tr>
                                    {response.result.columns.map((column) => (
                                        <th key={column}>{formatColumnLabel(column)}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {response.result.rows.map((row, index) => (
                                    <tr key={`query-row-${index}`}>
                                        {response.result.columns.map((column) => (
                                            <td key={`${index}-${column}`}>
                                                {column === pipelineField ? (
                                                    <button type="button" className="table-link" onClick={() => onOpenPipeline(row[column])}>
                                                        {row[column]}
                                                    </button>
                                                ) : (
                                                    renderQueryValue(row[column], column)
                                                )}
                                            </td>
                                        ))}
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                ) : (
                    <p className="empty-text">This query returned no rows.</p>
                )}
                <details className="detail-block ai-kql-block">
                    <summary>Generated KQL</summary>
                    <pre className="code-block query-sql">{response.display_kql}</pre>
                </details>
            </article>
        </section>
    );
}

async function fetchJson(url, options) {
    const response = await fetch(url, options);
    if (!response.ok) {
        const detail = await response.text();
        throw new Error(detail || "Request failed");
    }
    return response.json();
}

function buildQueryParams(filters) {
    const params = new URLSearchParams();
    params.set("window_days", String(filters.windowDays));
    if (filters.cadence) {
        params.set("cadence", filters.cadence);
    }
    if (filters.status) {
        params.set("status", filters.status);
    }
    if (filters.owner) {
        params.set("owner", filters.owner);
    }
    if (filters.criticality) {
        params.set("criticality", filters.criticality);
    }
    if (filters.search.trim()) {
        params.set("search", filters.search.trim());
    }
    return params.toString();
}

function toApiFilters(filters) {
    return {
        window_days: filters.windowDays,
        cadence: filters.cadence || null,
        status: filters.status || null,
        owner: filters.owner || null,
        criticality: filters.criticality || null,
        search: filters.search.trim() || null,
    };
}

function collectDistinctValues(groups, key) {
    const values = new Set();
    (groups || []).forEach((group) => {
        group.pipelines.forEach((pipeline) => {
            if (pipeline[key]) {
                values.add(pipeline[key]);
            }
        });
    });
    return Array.from(values).sort();
}

function mergeOptions(current, nextValues) {
    return Array.from(new Set([...(current || []), ...nextValues])).sort();
}

function flattenVisiblePipelines(groups) {
    return (groups || []).flatMap((group) => group.pipelines || []);
}

function safeNumber(value, fallback = 0) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
}

function percentBarWidth(value) {
    return `${clamp(safeNumber(value), 0, 100)}%`;
}

function scaledBarWidth(value, maxValue) {
    if (!maxValue) {
        return "0%";
    }
    return `${clamp((safeNumber(value) / maxValue) * 100, 0, 100)}%`;
}

function stackedBarWidth(value, total) {
    if (!total) {
        return "0%";
    }
    return `${clamp((safeNumber(value) / total) * 100, 0, 100)}%`;
}

function clamp(value, minimum, maximum) {
    return Math.min(maximum, Math.max(minimum, value));
}

function formatDuration(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "N/A";
    }
    const totalSeconds = Number(value);
    if (totalSeconds >= 3600) {
        return `${(totalSeconds / 3600).toFixed(1)}h`;
    }
    if (totalSeconds >= 60) {
        return `${(totalSeconds / 60).toFixed(1)}m`;
    }
    return `${Math.round(totalSeconds)}s`;
}

function formatDateTime(value) {
    if (!value) {
        return "N/A";
    }
    return new Date(value).toLocaleString(undefined, {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
    });
}

function formatPercent(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "N/A";
    }
    return `${Number(value).toFixed(1)}%`;
}

function formatTrend(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "Stable";
    }
    return `${value > 0 ? "+" : ""}${Number(value).toFixed(1)}%`;
}

function trendClassName(value) {
    if (value === null || value === undefined || Number.isNaN(Number(value))) {
        return "trend-neutral";
    }
    if (value > 15) {
        return "trend-up";
    }
    if (value < -10) {
        return "trend-down";
    }
    return "trend-neutral";
}

function successRateFillClassName(value) {
    const rate = safeNumber(value, 0);
    if (rate >= 95) {
        return "bar-fill-success";
    }
    if (rate >= 85) {
        return "bar-fill-warning";
    }
    return "bar-fill-danger";
}

function regressionFillClassName(value) {
    return safeNumber(value, 0) >= 25 ? "bar-fill-danger" : "bar-fill-warning";
}

function timelineDotClassName(status) {
    if (status === "Succeeded") {
        return "timeline-dot-success";
    }
    if (status === "InProgress") {
        return "timeline-dot-progress";
    }
    return "timeline-dot-danger";
}

function formatLabel(value) {
    if (!value) {
        return "N/A";
    }
    return String(value)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (match) => match.toUpperCase());
}

function formatPipelineDisplayName(value) {
    if (!value) {
        return "N/A";
    }
    return String(value)
        .replace(/_/g, " ")
        .replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        .trim();
}

function formatColumnLabel(value) {
    return String(value)
        .replace(/_/g, " ")
        .replace(/\b\w/g, (match) => match.toUpperCase());
}

function renderQueryValue(value, column) {
    if (value === null || value === undefined || value === "") {
        return "N/A";
    }
    if (column.includes("duration")) {
        return formatDuration(value);
    }
    if (column.includes("rate") || column.includes("pct")) {
        return formatPercent(value);
    }
    if (column.includes("start") || column.includes("date") || column.includes("retry_at")) {
        return formatDateTime(value);
    }
    return String(value);
}

function scaleDuration(durationSeconds, points) {
    const values = points.map((point) => point.duration_seconds || 0);
    const maxValue = Math.max(...values, 1);
    return ((durationSeconds || 0) / maxValue) * 100;
}
